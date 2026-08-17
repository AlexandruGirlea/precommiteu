from __future__ import annotations

import itertools
import logging
import os
import pathlib
import re
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from contextlib import ExitStack
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from precommiteu.agents.orchestrator import OrchestratorRun, run_orchestrator
from precommiteu.chunking import CanonicalChunk, token_chunks
from precommiteu.config import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_WALL_SECONDS_PER_FILE,
    MAX_SIBLING_STEMS,
    PROMOTE_CONFIDENCE,
    PROMOTE_SIMILARITY,
)
from precommiteu.debuglog import validator_debug
from precommiteu.defaults import (
    MISSING_MODELS_HINT,
    default_detector_adapter,
    default_orchestrator_model,
)
from precommiteu.direct import run_direct
from precommiteu.grammar import DETECTOR_GBNF, LOOP_STEP_GBNF, VALIDATOR_GBNF
from precommiteu.llama_server import launch_llama_server
from precommiteu.model_factory import build_chat_model
from precommiteu.regulations import (
    DEFAULT_REGULATION,
    get_regulation_pack,
    pack_article_ids,
)
from precommiteu.retrieval import CaseIndex
from precommiteu.scan_ledger import ScanLedger
from precommiteu.src.chunk_view import ChunkConsultLog
from precommiteu.src.eu_ignore_marker import (
    match_eu_ignore_marker_in_range,
    parse_eu_ignore_markers_for_scan_text,
)
from precommiteu.src.file_filter import MAX_SCAN_FILE_BYTES, collect_code_files
from precommiteu.src.ignore_directives import apply_prompt_ignore_directives
from precommiteu.src.regulations import article_for
from precommiteu.src.scanner import (
    _normalize_validator_article_id,
    _validator_evidence_visible,
    dedup_findings,
)
from precommiteu.src.schemas import Advisory, Finding, ScanResult, ScanStatus
from precommiteu.tools.sandbox import Sandbox

__all__ = [
    "DEFAULT_MERGE_TARGET",
    "GIT_MERGE_TARGET_BRANCH_ENV",
    "AdvisoryCallback",
    "FindingCallback",
    "GitDiffError",
    "ProgressCallback",
    "scan_diff",
    "scan_paths",
]

GIT_MERGE_TARGET_BRANCH_ENV = "GIT_MERGE_TARGET_BRANCH"
DEFAULT_MERGE_TARGET = "main"

_LOG = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], None]
FindingCallback = Callable[[Finding], None]
AdvisoryCallback = Callable[[Advisory], None]


@dataclass
class _RegCounters:
    detector_candidates: int = 0
    validator_rejected: int = 0
    chunks_scanned: int = 0
    files_errored: int = 0


_ANALYSIS_FAILURE_REASONS = frozenset({"loop_step_failed", "direct_partial"})

# The file was analysed end to end. Every other ending (budget exhausted, a
# failed step, an unreadable file) leaves work undone, so it is never recorded
# in the scan ledger and the next run scans it again.
_CLEAN_EXIT_REASONS = frozenset({"direct", "emit"})

# Orchestrator endings that leave a file unanalysed while budget remains.
# loop_step_failed is absent on purpose: it already reports as a failed file.
# budget_exhausted_time is absent because it means the wall clock is spent,
# so a fallback would be handed a zero budget and do nothing.
_UNANALYSED_REASONS = frozenset({"emit", "budget_exhausted_iters"})


def _maybe_call(cb: Callable[..., Any] | None, payload: Any) -> None:
    if cb is None:
        return
    try:
        cb(payload)
    except Exception as exc:
        _LOG.warning("callback raised: %r", exc)


def _file_label(path: pathlib.Path, repo_root: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def _article_known(regulation: str, article_id: str) -> bool:
    try:
        if article_for(regulation, article_id):
            return True
    except ValueError:
        pass
    return article_id in pack_article_ids(regulation)


def _resolve_evidence_chunk(
    chunks: list[CanonicalChunk],
    evidence: str,
) -> CanonicalChunk | None:
    if not chunks:
        return None
    for c in chunks:
        if evidence and evidence in c.text:
            return c
    return chunks[0]


def _evidence_line_range(
    chunk: CanonicalChunk,
    evidence: str,
) -> tuple[int, int]:
    text = evidence.strip()
    if not text:
        return chunk.start_line, chunk.end_line
    span = text.count("\n")
    index = chunk.text.find(text)
    if index >= 0:
        start = chunk.start_line + chunk.text.count("\n", 0, index)
        return start, min(start + span, chunk.end_line)
    first = " ".join(text.splitlines()[0].split())
    if first:
        for offset, line in enumerate(chunk.text.splitlines()):
            if first in " ".join(line.split()):
                start = chunk.start_line + offset
                return start, min(start + span, chunk.end_line)
    return chunk.start_line, chunk.end_line


def _build_finding(
    *,
    regulation: str,
    chunk: CanonicalChunk,
    file_label: str,
    article_id: str,
    description: str,
    evidence: str,
    inline_markers: list,
) -> Finding:
    start_line, end_line = _evidence_line_range(chunk, evidence)
    finding = Finding(
        regulation=regulation,
        source="precommiteu",
        file=file_label,
        start_line=start_line,
        end_line=end_line,
        probable_article_id=article_id,
        code_evidence=evidence,
        description=description,
    )
    hit = match_eu_ignore_marker_in_range(
        finding.probable_article_id,
        finding.start_line,
        finding.end_line,
        inline_markers,
    )
    if hit is not None:
        finding.eu_ignore_reason = hit.reason
        finding.eu_ignore_source = "inline"
    return finding


def _translate_kept_findings(
    *,
    regulation: str,
    file_label: str,
    chunks: list[CanonicalChunk],
    consult_log: ChunkConsultLog,
    kept_findings: list[dict[str, Any]],
    inline_markers: list,
) -> tuple[list[Finding], int]:
    consulted_text = consult_log.consulted_text()
    findings_out: list[Finding] = []
    accepted = 0
    debug = bool(os.environ.get("PRECOMMITEU_DEBUG_RAW"))

    for vf in kept_findings:
        raw_article = (vf.get("article_no") or "").strip()
        article_id: str | None = _normalize_validator_article_id(raw_article, regulation)
        drop_reason = None
        if not article_id:
            drop_reason = "article_unparseable"
        elif not _article_known(regulation, article_id):
            drop_reason = "article_not_in_registry"

        evidence = (vf.get("code_evidence") or "").strip()
        description = (vf.get("description") or "").strip()
        evidence_visible = _validator_evidence_visible(evidence, consulted_text)
        if drop_reason is None:
            if not description:
                drop_reason = "description_missing"
            elif not evidence:
                drop_reason = "evidence_missing"
            elif not evidence_visible:
                drop_reason = "evidence_not_visible"

        validator_debug(
            {
                "stage": "translate",
                "file_label": file_label,
                "regulation": regulation,
                "outcome": "drop" if drop_reason else "keep",
                "reason": drop_reason,
                "article_raw": raw_article,
                "article_id": article_id,
                "evidence": evidence[:200],
                "description": description[:200],
                "consulted_chars": len(consulted_text),
            }
        )
        if drop_reason:
            if debug:
                print(
                    f"[precommiteu:debug] validator {regulation} {file_label}: "
                    f"DROP reason={drop_reason!r} article={raw_article!r} "
                    f"evidence={evidence[:80]!r} {description[:80]!r}",
                    file=sys.stderr,
                )
            continue

        host_chunk = next(
            (c for c in chunks if c.id == vf.get("chunk_id")), None
        ) or _resolve_evidence_chunk(chunks, evidence)
        if host_chunk is None:
            continue

        finding = _build_finding(
            regulation=regulation,
            chunk=host_chunk,
            file_label=file_label,
            article_id=article_id,
            description=description,
            evidence=evidence,
            inline_markers=inline_markers,
        )
        findings_out.append(finding)
        accepted += 1

    rejected = max(0, len(kept_findings) - accepted)
    return findings_out, rejected


def _references_siblings(text: str, file_path: pathlib.Path) -> bool:
    try:
        stems = set(
            itertools.islice(
                (
                    p.stem
                    for p in file_path.parent.iterdir()
                    if p.is_file() and p != file_path and len(p.stem) >= 3
                ),
                MAX_SIBLING_STEMS,
            )
        )
    except OSError:
        return False
    if not stems:
        return False
    pattern = re.compile(
        r"\b(?:" + "|".join(map(re.escape, sorted(stems))) + r")\b"
    )
    return bool(pattern.search(text))


def _load_case_index(regulation: str) -> CaseIndex | None:
    try:
        resource = files(f"precommiteu.regulations.{regulation}") / "cases.jsonl"
        if not resource.is_file():
            _LOG.info(
                "no case index packaged for %r; retrieval promotion disabled",
                regulation,
            )
            return None
        index = CaseIndex.loads(resource.read_text(encoding="utf-8"))
    except Exception as exc:
        _LOG.warning("case index unavailable for %r: %s", regulation, exc)
        return None
    _LOG.info("case index loaded for %r: %d cases", regulation, len(index))
    return index


def _apply_retrieval(
    *,
    case_index: CaseIndex,
    file_advisories: list[Advisory],
    code: str,
    regulation: str,
    chunks: list[CanonicalChunk],
    inline_markers: list,
) -> tuple[list[Finding], list[Advisory]]:
    promoted: list[Finding] = []
    remaining: list[Advisory] = []
    for raw_adv in file_advisories:
        verdict = case_index.score(code, raw_adv.description)
        adv = raw_adv.model_copy(
            update={
                "retrieval_verdict": verdict.verdict,
                "retrieval_confidence": verdict.confidence,
                "retrieval_similarity": verdict.similarity,
                "retrieval_article_id": verdict.probable_article_id,
            }
        )
        article = (
            _normalize_validator_article_id(verdict.probable_article_id, regulation)
            if verdict.probable_article_id
            else None
        )
        article_ok = bool(article) and _article_known(regulation, article)
        if (
            verdict.verdict == "violation_pattern"
            and verdict.confidence >= PROMOTE_CONFIDENCE
            and verdict.similarity >= PROMOTE_SIMILARITY
            and article_ok
            and chunks
        ):
            finding = Finding(
                regulation=regulation,
                source="retrieval",
                file=adv.file,
                start_line=chunks[0].start_line,
                end_line=chunks[0].end_line,
                probable_article_id=article,
                code_evidence=None,
                description=(
                    f"{adv.description} [matches a known violation pattern: "
                    f"{article}, similarity {verdict.similarity:.2f}]"
                ),
            )
            hit = match_eu_ignore_marker_in_range(
                article, finding.start_line, finding.end_line, inline_markers
            )
            if hit is not None:
                finding.eu_ignore_reason = hit.reason
                finding.eu_ignore_source = "inline"
            promoted.append(finding)
        else:
            remaining.append(adv)
    return promoted, remaining


def _scan_one_file(
    *,
    file_path: pathlib.Path,
    regulation: str,
    repo_root: pathlib.Path,
    regulation_docs_dir: pathlib.Path,
    loop_model: Any,
    detector_model: Any,
    validator_model: Any,
    max_iterations: int,
    wall_seconds_per_file: float,
    counters: _RegCounters,
    on_progress: ProgressCallback | None,
    on_finding: FindingCallback | None,
    advisories: list[Advisory],
    on_advisory: AdvisoryCallback | None = None,
    case_index: CaseIndex | None = None,
    agent_mode: str = "auto",
) -> tuple[list[Finding], bool]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _LOG.warning("scan: cannot read %s: %s", file_path, exc)
        counters.files_errored += 1
        _maybe_call(
            on_progress,
            {
                "event": "file_error",
                "file": _file_label(file_path, repo_root),
                "regulation": regulation,
                "error": f"unreadable: {exc!r}",
            },
        )
        return [], False

    file_label = _file_label(file_path, repo_root)
    filtered_text = apply_prompt_ignore_directives(text)
    if filtered_text is None:
        _maybe_call(
            on_progress,
            {"event": "file_ignored", "file": file_label, "regulation": regulation},
        )
        return [], False

    inline_markers = parse_eu_ignore_markers_for_scan_text(text)
    chunks = token_chunks(file_path, filtered_text)
    counters.chunks_scanned += len(chunks)

    _maybe_call(
        on_progress,
        {
            "event": "file_start",
            "file": file_label,
            "regulation": regulation,
            "chunks": len(chunks),
        },
    )

    scan_root = file_path.parent.resolve()

    use_orchestrator = agent_mode == "orchestrator" or (
        agent_mode == "auto" and _references_siblings(filtered_text, file_path)
    )
    fell_back = False
    if use_orchestrator:
        code_sandbox = Sandbox((scan_root,))
        regulation_sandbox = Sandbox((regulation_docs_dir,))
        started = time.monotonic()
        run: OrchestratorRun = run_orchestrator(
            file_path=file_path,
            regulation=regulation,
            loop_model=loop_model,
            detector_model=detector_model,
            validator_model=validator_model,
            sandbox=code_sandbox,
            regulation_sandbox=regulation_sandbox,
            regulation_docs_dir=regulation_docs_dir,
            max_iterations=max_iterations,
            wall_seconds=wall_seconds_per_file,
        )
        if not run.detector_called and run.exit_reason in _UNANALYSED_REASONS:
            # The agent stopped without ever reaching the detector, so the
            # file is unanalysed. Scan it directly rather than report it
            # clean, within whatever is left of the per-file budget.
            _LOG.warning(
                "scan: orchestrator ended %r on %s without calling the "
                "detector; falling back to the direct route",
                run.exit_reason,
                file_label,
            )
            fell_back = True
            run = run_direct(
                chunks=chunks,
                file_label=file_label,
                detector_model=detector_model,
                validator_model=validator_model,
                regulation_pack=get_regulation_pack(regulation),
                wall_seconds=max(
                    0.0, wall_seconds_per_file - (time.monotonic() - started)
                ),
            )
    else:
        run = run_direct(
            chunks=chunks,
            file_label=file_label,
            detector_model=detector_model,
            validator_model=validator_model,
            regulation_pack=get_regulation_pack(regulation),
            wall_seconds=wall_seconds_per_file,
        )

    _maybe_call(
        on_progress,
        {
            "event": "orchestrator_done",
            "file": file_label,
            "regulation": regulation,
            "route": "orchestrator" if use_orchestrator else "direct",
            "fell_back": fell_back,
            "detector_called": run.detector_called,
            "validator_called": run.validator_called,
            "kept_raw": len(run.kept_findings),
            "tool_calls": run.tool_call_count,
            "exit_reason": run.exit_reason,
        },
    )

    if run.exit_reason in _ANALYSIS_FAILURE_REASONS:
        counters.files_errored += 1
        _maybe_call(
            on_progress,
            {
                "event": "file_error",
                "file": file_label,
                "regulation": regulation,
                "error": run.exit_reason,
            },
        )

    counters.detector_candidates += sum(
        len(run.candidates_store.get(label))
        for label in run.candidates_store.labels()
    )

    findings_out, rejected = _translate_kept_findings(
        regulation=regulation,
        file_label=file_label,
        chunks=chunks,
        consult_log=run.consult_log,
        kept_findings=run.kept_findings,
        inline_markers=inline_markers,
    )
    counters.validator_rejected += rejected

    if not findings_out:
        seen: set[str] = set()
        file_advisories: list[Advisory] = []
        for label in run.candidates_store.labels():
            for candidate in run.candidates_store.get(label):
                description = (candidate.get("description") or "").strip()
                if description and description not in seen:
                    seen.add(description)
                    file_advisories.append(
                        Advisory(
                            regulation=regulation,
                            file=file_label,
                            description=description,
                        )
                    )
        if case_index is not None and file_advisories:
            promoted, file_advisories = _apply_retrieval(
                case_index=case_index,
                file_advisories=file_advisories,
                code=filtered_text,
                regulation=regulation,
                chunks=chunks,
                inline_markers=inline_markers,
            )
            findings_out.extend(promoted)
        for advisory in file_advisories:
            advisories.append(advisory)
            if on_advisory is not None:
                try:
                    on_advisory(advisory)
                except Exception as exc:
                    _LOG.warning("advisory callback raised: %r", exc)

    for f in findings_out:
        _maybe_call(on_progress, {"event": "finding", "file": file_label})
        if on_finding is not None:
            try:
                on_finding(f)
            except Exception as exc:
                _LOG.warning("finding callback raised: %r", exc)

    _maybe_call(
        on_progress,
        {
            "event": "file_done",
            "file": file_label,
            "regulation": regulation,
            "kept": len(findings_out),
        },
    )

    return findings_out, run.exit_reason in _CLEAN_EXIT_REASONS


def scan_paths(
    paths: Iterable[str | pathlib.Path],
    *,
    regulations: tuple[str, ...] = (DEFAULT_REGULATION,),
    orchestrator_model_path: pathlib.Path | None = None,
    detector_adapter_path: pathlib.Path | None = None,
    detector_grammar_path: pathlib.Path | None = None,
    agent_mode: str = "auto",
    n_ctx: int = 32768,
    n_gpu_layers: int = 99,
    threads: int | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    wall_seconds_per_file: float = DEFAULT_WALL_SECONDS_PER_FILE,
    on_progress: ProgressCallback | None = None,
    on_finding: FindingCallback | None = None,
    on_advisory: AdvisoryCallback | None = None,
    repo_root: pathlib.Path | None = None,
    regulation_docs_dir: pathlib.Path | None = None,
    max_file_bytes: int | None = MAX_SCAN_FILE_BYTES,
    incremental: bool = True,
    rescan_all: bool = False,
    scan_log: pathlib.Path | None = None,
) -> ScanResult:
    started_at = time.monotonic()
    repo_root = (repo_root or pathlib.Path.cwd()).resolve()
    if regulation_docs_dir is None:
        regulation_docs_dir = pathlib.Path(__file__).resolve().parent / "regulations"

    if orchestrator_model_path is None:
        orchestrator_model_path = default_orchestrator_model()
    if orchestrator_model_path is None:
        raise ValueError(f"no model paths configured; {MISSING_MODELS_HINT}")

    raw_paths = [pathlib.Path(p).expanduser() for p in paths]
    selected_files, oversized = collect_code_files(
        raw_paths,
        repo_root,
        skip_tests=True,
        max_bytes=max_file_bytes,
    )
    if oversized:
        _LOG.warning(
            "%d file(s) skipped for exceeding %s bytes: %s",
            len(oversized),
            max_file_bytes,
            ", ".join(str(p) for p in oversized[:10]),
        )
        _maybe_call(
            on_progress,
            {"event": "files_oversized", "files": [str(p) for p in oversized]},
        )

    _maybe_call(
        on_progress,
        {
            "event": "scan_start",
            "files_total": len(selected_files),
            "regulations": list(regulations),
        },
    )

    detector_grammar = (
        pathlib.Path(detector_grammar_path).read_text(encoding="utf-8")
        if detector_grammar_path is not None
        else DETECTOR_GBNF
    )

    if agent_mode not in ("auto", "direct", "orchestrator"):
        raise ValueError(f"unknown agent_mode: {agent_mode!r}")
    counters: dict[str, _RegCounters] = {r: _RegCounters() for r in regulations}
    all_findings: list[Finding] = []
    all_advisories: list[Advisory] = []
    statuses: list[ScanStatus] = []
    case_indexes = {r: _load_case_index(r) for r in regulations}
    files_total = len(selected_files)
    interrupted_after: dict[str, int] = {}

    ledgers: dict[str, ScanLedger] = {}
    pending = {r: list(selected_files) for r in regulations}
    reused = dict.fromkeys(regulations, 0)
    if incremental:
        if scan_log is not None and len(regulations) > 1:
            raise ValueError(
                "one scan_log cannot serve several regulations; a ledger "
                "records one regulation only"
            )
        for regulation in regulations:
            ledger = ScanLedger.load(repo_root, regulation, scan_log)
            ledgers[regulation] = ledger
            todo: list[pathlib.Path] = []
            for file_path in selected_files:
                label = _file_label(file_path, repo_root)
                hit = None if rescan_all else ledger.reuse(label)
                if hit is None:
                    todo.append(file_path)
                    continue
                past_findings, past_advisories = hit
                all_findings.extend(past_findings)
                all_advisories.extend(past_advisories)
                _maybe_call(
                    on_progress,
                    {
                        "event": "file_reused",
                        "file": label,
                        "regulation": regulation,
                        "kept": len(past_findings),
                    },
                )
                for finding in past_findings:
                    _maybe_call(on_finding, finding)
                for advisory in past_advisories:
                    _maybe_call(on_advisory, advisory)
            pending[regulation] = todo
            reused[regulation] = files_total - len(todo)
            ledger.save()
            _maybe_call(
                on_progress,
                {
                    "event": "ledger_loaded",
                    "regulation": regulation,
                    "path": str(ledger.path),
                    "reused": reused[regulation],
                    "to_scan": len(pending[regulation]),
                },
            )

    if any(pending.values()):
        base_model = pathlib.Path(orchestrator_model_path)
        explicit_adapter = (
            pathlib.Path(detector_adapter_path)
            if detector_adapter_path is not None
            else None
        )
        with ExitStack() as base_stack:
            try:
                base_handle = base_stack.enter_context(
                    launch_llama_server(
                        base_model,
                        n_ctx=n_ctx,
                        n_gpu_layers=n_gpu_layers,
                        n_threads=threads,
                    )
                )
            except Exception as exc:
                _LOG.error("scan: failed to launch llama-servers: %s", exc)
                raise

            orchestrator_loop_model = build_chat_model(base_handle, grammar=LOOP_STEP_GBNF)
            validator_model = build_chat_model(base_handle, grammar=VALIDATOR_GBNF)

            for reg_index, regulation in enumerate(regulations):
                if not pending[regulation]:
                    continue
                ledger = ledgers.get(regulation)
                reg_adapter = explicit_adapter
                if reg_adapter is None:
                    candidate = default_detector_adapter(regulation, base_model.parent)
                    reg_adapter = candidate if candidate and candidate.exists() else None
                if reg_adapter is None:
                    _LOG.warning(
                        "no detector adapter for %r; scanning with the base model only "
                        "(degraded mode)",
                        regulation,
                    )
                _maybe_call(
                    on_progress,
                    {
                        "event": "detector_adapter",
                        "regulation": regulation,
                        "adapter": (
                            f"{reg_adapter.parent.name}/{reg_adapter.name}"
                            if reg_adapter is not None
                            else "base model (degraded)"
                        ),
                    },
                )

                with ExitStack() as detector_stack:
                    if reg_adapter is not None:
                        detector_handle = detector_stack.enter_context(
                            launch_llama_server(
                                base_model,
                                n_ctx=n_ctx,
                                n_gpu_layers=n_gpu_layers,
                                n_threads=threads,
                                lora_path=reg_adapter,
                            )
                        )
                    else:
                        detector_handle = base_handle
                    detector_model = build_chat_model(
                        detector_handle, grammar=detector_grammar
                    )

                    files_done = reused[regulation]
                    for file_path in pending[regulation]:
                        label = _file_label(file_path, repo_root)
                        stamp = ledger.stamp(label) if ledger is not None else None
                        advisory_mark = len(all_advisories)
                        try:
                            findings_out, analysed = _scan_one_file(
                                case_index=case_indexes[regulation],
                                agent_mode=agent_mode,
                                file_path=file_path,
                                regulation=regulation,
                                repo_root=repo_root,
                                regulation_docs_dir=regulation_docs_dir,
                                loop_model=orchestrator_loop_model,
                                detector_model=detector_model,
                                validator_model=validator_model,
                                max_iterations=max_iterations,
                                wall_seconds_per_file=wall_seconds_per_file,
                                counters=counters[regulation],
                                on_progress=on_progress,
                                on_finding=on_finding,
                                advisories=all_advisories,
                                on_advisory=on_advisory,
                            )
                        except KeyboardInterrupt:
                            interrupted_after[regulation] = files_done
                            for later in regulations[reg_index + 1:]:
                                interrupted_after[later] = reused[later]
                            _maybe_call(
                                on_progress,
                                {
                                    "event": "scan_interrupted",
                                    "files_done": files_done,
                                    "files_total": files_total,
                                },
                            )
                            break
                        except Exception as exc:
                            _LOG.exception(
                                "scan: %s failed under %s", file_path, regulation
                            )
                            counters[regulation].files_errored += 1
                            _maybe_call(
                                on_progress,
                                {
                                    "event": "file_error",
                                    "file": label,
                                    "regulation": regulation,
                                    "error": repr(exc),
                                },
                            )
                        else:
                            all_findings.extend(findings_out)
                            if ledger is not None and analysed:
                                ledger.record(
                                    label,
                                    stamp,
                                    findings_out,
                                    all_advisories[advisory_mark:],
                                )
                                ledger.save()
                        files_done += 1
                if interrupted_after:
                    break

    for regulation in regulations:
        c = counters[regulation]
        detail_parts: list[str] = []
        if regulation in interrupted_after:
            detail_parts.append(
                f"interrupted after {interrupted_after[regulation]} of "
                f"{files_total} files"
            )
        if c.files_errored:
            detail_parts.append(
                f"{c.files_errored} file(s) could not be scanned. "
                "results incomplete"
            )
        if reused[regulation]:
            detail_parts.append(
                f"{reused[regulation]} of {files_total} file(s) reused "
                "unchanged from the scan ledger"
            )
        statuses.append(
            ScanStatus(
                regulation=regulation,
                status="failed" if c.files_errored else "scanned",
                detail="; ".join(detail_parts) or None,
                chunks_scanned=c.chunks_scanned,
                detector_candidates=c.detector_candidates,
                validator_rejected=c.validator_rejected,
            )
        )

    unique = dedup_findings(all_findings)
    _maybe_call(
        on_progress,
        {
            "event": "scan_done",
            "findings_total": len(unique),
            "advisories_total": len(all_advisories),
            "files_reused": sum(reused.values()),
            "elapsed_ms": int((time.monotonic() - started_at) * 1000),
        },
    )
    return ScanResult(findings=unique, statuses=statuses, advisories=all_advisories)


class GitDiffError(RuntimeError):
    pass


def _run_git(args: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _run_git_bytes(
    args: list[str], cwd: pathlib.Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        check=False,
    )


def _require_git_repo(cwd: pathlib.Path) -> None:
    proc = _run_git(["rev-parse", "--git-dir"], cwd)
    if proc.returncode != 0:
        raise GitDiffError(
            "--ci requires a git repository; current dir is not a git checkout"
        )


def _resolve_merge_target(merge_target: str, cwd: pathlib.Path) -> str:
    local = _run_git(["rev-parse", "--verify", "--quiet", merge_target], cwd)
    if local.returncode == 0 and local.stdout.strip():
        return merge_target
    origin_ref = f"origin/{merge_target}"
    remote = _run_git(["rev-parse", "--verify", "--quiet", origin_ref], cwd)
    if remote.returncode == 0 and remote.stdout.strip():
        return origin_ref
    raise GitDiffError(
        f"cannot resolve merge target: neither '{merge_target}' nor "
        f"'{origin_ref}' is a known git ref. Set {GIT_MERGE_TARGET_BRANCH_ENV} "
        "to a branch that exists in this checkout."
    )


def _changed_files(target_ref: str, cwd: pathlib.Path) -> list[pathlib.Path]:
    # -z: NUL-separated raw paths, immune to quotePath escaping of
    # non-ASCII filenames.
    proc = _run_git_bytes(
        [
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            "--diff-filter=AM",
            f"{target_ref}...HEAD",
        ],
        cwd,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        raise GitDiffError(
            f"git diff failed against {target_ref}: {stderr.strip()}"
        )
    out: list[pathlib.Path] = []
    for raw_name in proc.stdout.split(b"\0"):
        if not raw_name:
            continue
        candidate = (cwd / os.fsdecode(raw_name)).resolve()
        if candidate.exists() and candidate.is_file():
            out.append(candidate)
    return out


def scan_diff(
    *,
    merge_target: str | None = None,
    regulations: tuple[str, ...] = (DEFAULT_REGULATION,),
    orchestrator_model_path: pathlib.Path | None = None,
    detector_adapter_path: pathlib.Path | None = None,
    detector_grammar_path: pathlib.Path | None = None,
    agent_mode: str = "auto",
    n_ctx: int = 32768,
    n_gpu_layers: int = 99,
    threads: int | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    wall_seconds_per_file: float = DEFAULT_WALL_SECONDS_PER_FILE,
    on_progress: ProgressCallback | None = None,
    on_finding: FindingCallback | None = None,
    on_advisory: AdvisoryCallback | None = None,
    repo_root: pathlib.Path | None = None,
    regulation_docs_dir: pathlib.Path | None = None,
    max_file_bytes: int | None = MAX_SCAN_FILE_BYTES,
) -> ScanResult:
    cwd = (repo_root or pathlib.Path.cwd()).resolve()
    _require_git_repo(cwd)

    target = merge_target or os.environ.get(
        GIT_MERGE_TARGET_BRANCH_ENV, DEFAULT_MERGE_TARGET
    )
    resolved_ref = _resolve_merge_target(target, cwd)
    files = _changed_files(resolved_ref, cwd)

    _maybe_call(
        on_progress,
        {
            "event": "ci_diff_resolved",
            "merge_target": target,
            "resolved_ref": resolved_ref,
            "changed_files": [str(p) for p in files],
        },
    )

    if not files:
        return ScanResult(
            findings=[],
            statuses=[
                ScanStatus(
                    regulation=r,
                    status="scanned",
                    detail="no files changed vs merge target",
                    chunks_scanned=0,
                    detector_candidates=0,
                    validator_rejected=0,
                )
                for r in regulations
            ],
        )

    return scan_paths(
        files,
        regulations=regulations,
        orchestrator_model_path=orchestrator_model_path,
        detector_adapter_path=detector_adapter_path,
        detector_grammar_path=detector_grammar_path,
        agent_mode=agent_mode,
        n_ctx=n_ctx,
        n_gpu_layers=n_gpu_layers,
        threads=threads,
        max_iterations=max_iterations,
        wall_seconds_per_file=wall_seconds_per_file,
        on_progress=on_progress,
        on_finding=on_finding,
        on_advisory=on_advisory,
        repo_root=cwd,
        regulation_docs_dir=regulation_docs_dir,
        max_file_bytes=max_file_bytes,
        # Every file here is changed vs the merge target, so a ledger would
        # never hit; and CI runners are meant to keep no state between runs.
        incremental=False,
    )
