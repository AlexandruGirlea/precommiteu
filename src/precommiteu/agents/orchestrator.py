from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from precommiteu.agents import prompts
from precommiteu.agents.react_loop import run_react_loop
from precommiteu.chunking import APPROX_TOKENS, CanonicalChunk, token_chunks, token_counter
from precommiteu.config import DEFAULT_WALL_SECONDS_PER_FILE, ENRICHMENT_DEPTH_CAP
from precommiteu.regulations import get_regulation_pack
from precommiteu.src.chunk_view import ChunkConsultLog
from precommiteu.src.ignore_directives import apply_prompt_ignore_directives
from precommiteu.tools import read_tools, regulation_tools
from precommiteu.tools.detector_tool import build_call_detector_tool
from precommiteu.tools.find_references import find_references
from precommiteu.tools.sandbox import Sandbox
from precommiteu.tools.validator_tool import (
    CandidatesStore,
    EnrichedCodeStore,
    build_call_validator_tool,
)

_DEBUG_ENRICH = bool(os.environ.get("PRECOMMITEU_DEBUG_ENRICH"))


def _debug_emit(payload: dict[str, Any]) -> None:
    if not _DEBUG_ENRICH:
        return
    try:
        sys.stderr.write("PRECOMMITEU_DEBUG_ENRICH " + json.dumps(payload) + "\n")
        sys.stderr.flush()
    except Exception:
        pass

__all__ = [
    "OrchestratorRun",
    "run_orchestrator",
]

_LOG = logging.getLogger(__name__)

@dataclass
class OrchestratorRun:
    kept_findings: list[dict[str, Any]] = field(default_factory=list)
    consult_log: ChunkConsultLog = field(default_factory=ChunkConsultLog)
    candidates_store: CandidatesStore = field(default_factory=CandidatesStore)
    tool_call_count: int = 0
    exit_reason: str = ""
    detector_called: bool = False
    validator_called: bool = False
    enriched_chunks: dict[str, str] = field(default_factory=dict)


def _initial_user_message(
    file_path: pathlib.Path,
    file_label: str,
    chunks: list[CanonicalChunk],
) -> str:
    first = chunks[0] if chunks else None
    first_block = (
        f'<chunk id="{first.id}" lines="{first.start_line}-{first.end_line}">\n'
        f"{first.text}\n"
        "</chunk>"
        if first is not None
        else "(file has no chunks)"
    )
    chunk_index = (
        "  (no chunks)"
        if not chunks
        else "\n".join(
            f"  - {c.id}: lines {c.start_line}-{c.end_line}" for c in chunks
        )
    )
    return (
        f"File: {file_label}\n"
        f"Absolute path: {file_path}\n\n"
        "Chunk index:\n"
        f"{chunk_index}\n\n"
        "First chunk inlined:\n"
        f"{first_block}\n\n"
        "The current chunk is fully inlined; do not reread it. "
        "Resolve relevant external symbols, if any, with "
        "find_references before detection. Source text is supplied by the runtime: "
        "use call_detector() without copying code, even if this chunk looks "
        "harmless. The runtime advances chunks after detection and validation."
    )


def _build_tools_map(
    *,
    regulation: str,
    sandbox: Sandbox,
    regulation_sandbox: Sandbox,
    regulation_docs_dir: pathlib.Path,
    consult_log: ChunkConsultLog,
    enriched_code_store: EnrichedCodeStore,
    target_file_resolved: str,
    target_file_label: str,
    detector_impl: Callable[..., str],
    validator_impl: Callable[..., str],
    counters: dict[str, int],
    todos: list[str],
    state: dict,
) -> dict[str, Callable[..., Any]]:
    repo_root = sandbox.roots[0]

    def _is_non_target(path_str: str) -> bool:
        try:
            resolved = pathlib.Path(path_str).resolve()
        except OSError:
            return False
        return str(resolved) != target_file_resolved

    def _enrichment_budget_error() -> str:
        return json.dumps(
            {
                "error": (
                    "enrichment_depth_cap_reached: at most "
                    f"{ENRICHMENT_DEPTH_CAP} external snippet allowed per "
                    "target chunk. Call call_detector with what you have."
                )
            }
        )

    def _try_increment_for_non_target(path_str: str) -> str | None:
        if not _is_non_target(path_str):
            return None
        if counters["enrichment_depth"] >= ENRICHMENT_DEPTH_CAP:
            return _enrichment_budget_error()
        counters["enrichment_depth"] += 1
        return None

    def _read_file(path: str, start_line: int = 1, end_line: int = 200) -> str:
        result = read_tools.read_file(
            sandbox, path, start_line=start_line, end_line=end_line
        )
        text = result.get("text", "")
        resolved_path = result.get("path", path)
        block = _try_increment_for_non_target(resolved_path)
        if block is not None:
            return block
        if text:
            key = f"{result['path']}:{result['start_line']}-{result['end_line']}"
            consult_log.record(key, text)
            if _is_non_target(resolved_path):
                state["searched"] = True
                source = "\n".join(line.split(" | ", 1)[-1] for line in text.splitlines())
                state["snippets"].append(f"\n\n# --- enriched: {key} ---\n{source}")
        return json.dumps(result)

    def _list_dir(path: str = ".", depth: int = 1) -> str:
        return json.dumps(read_tools.list_dir(sandbox, path, depth=depth))

    def _glob(pattern: str) -> str:
        return json.dumps(read_tools.glob(sandbox, pattern))

    def _grep(pattern: str, path: str = ".", file_glob: str = "**/*") -> str:
        return json.dumps(
            read_tools.grep(sandbox, pattern, path=path, file_glob=file_glob)
        )

    def _find_references(symbol: str) -> str:
        state["searched"] = True
        hits = find_references(
            sandbox, symbol, repo_root, exclude_file=pathlib.Path(target_file_resolved),
        )
        non_target_hits = [h for h in hits if _is_non_target(h.get("file", ""))]
        _debug_emit(
            {
                "event": "find_references",
                "target_file": target_file_label,
                "symbol": symbol,
                "hits_total": len(hits),
                "hits_cross_file": len(non_target_hits),
                "hit_files": sorted(
                    {h.get("file", "") for h in hits if h.get("file")}
                ),
                "depth_before": counters["enrichment_depth"],
                "depth_cap": ENRICHMENT_DEPTH_CAP,
            }
        )
        if non_target_hits:
            if counters["enrichment_depth"] >= ENRICHMENT_DEPTH_CAP:
                return _enrichment_budget_error()
            counters["enrichment_depth"] += 1
            for hit in non_target_hits[:1]:
                hit_file = hit.get("file", "")
                try:
                    rel = (
                        pathlib.Path(hit_file)
                        .resolve()
                        .relative_to(repo_root)
                        .as_posix()
                    )
                except (OSError, ValueError):
                    rel = pathlib.Path(hit_file).name
                span = f"{hit['start_line']}-{hit['end_line']}"
                snippet = hit.get("snippet", "")
                state["snippets"].append(
                    f"\n\n# --- enriched: {rel}:{span} ---\n{snippet}"
                )
                consult_log.record(f"{hit_file}:{span}", snippet)
        return json.dumps(hits)

    def _read_article(article_id: str, summary: bool = False) -> str:
        return json.dumps(
            regulation_tools.read_article(
                regulation_sandbox,
                regulation_docs_dir,
                article_id,
                summary=summary,
                regulation=regulation,
            )
        )

    def _list_articles() -> str:
        return json.dumps(
            regulation_tools.list_articles(
                regulation_sandbox, regulation_docs_dir, regulation=regulation
            )
        )

    def _grep_regulation(pattern: str) -> str:
        return json.dumps(
            regulation_tools.grep_regulation(
                regulation_sandbox, regulation_docs_dir, pattern, regulation=regulation
            )
        )

    def _call_detector(enriched_code: str = "", file_label: str = "") -> str:
        chunk = state["chunk"]
        if not state["searched"] and re.search(r"\b(?:from|import)\b|\w+\.\w+", chunk.text):
            return "ERROR: first use find_references on a relevant external symbol."
        if chunk.id in state["detected"]:
            return "Detection is complete for this chunk; call call_validator()."
        label = target_file_label
        if state["snippets"]:
            state["last_snippets"] = state["snippets"][:]
        snippets = state["snippets"] or (
            state["last_snippets"] if state["searched"] else []
        )
        composed = chunk.text + "".join(snippets)
        consult_log.record(chunk.id, chunk.text)
        enriched_code_store.put(chunk.id, composed)
        if _DEBUG_ENRICH:
            try:
                target_basename = target_file_label.split("/")[-1]
                files_in_blob = sorted(
                    {
                        p.name
                        for p in pathlib.Path(repo_root).glob("*")
                        if (
                            p.is_file()
                            and p.name in composed
                            and p.name != target_basename
                        )
                    }
                )
            except Exception:
                files_in_blob = []
            _debug_emit(
                {
                    "event": "call_detector",
                    "file_label": label,
                    "target_file": target_file_label,
                    "chunk_id": chunk.id,
                    "enriched_code_chars": len(composed),
                    "enriched_code_tokens": APPROX_TOKENS(composed),
                    "source_files_referenced": files_in_blob,
                    "enrichment_depth": counters["enrichment_depth"],
                    "detector_call_index": counters["detector_calls"],
                }
            )
        try:
            result = detector_impl(enriched_code=composed, file_label=chunk.id)
        except Exception:
            counters["detector_errors"] += 1
            raise
        counters["detector_calls"] += 1
        state["detected"].add(chunk.id)
        if not json.loads(result):
            state["completed"].add(chunk.id)
        return result

    def _call_validator(article_id_hint: str = "") -> str:
        chunk = state["chunk"]
        if chunk.id not in state["detected"]:
            return "ERROR: call call_detector() before validation."
        try:
            result = validator_impl(article_id_hint=article_id_hint)
        except Exception:
            counters["validator_errors"] += 1
            raise
        counters["validator_calls"] += 1
        state["completed"].add(chunk.id)
        return result

    todo_items = todos

    def _write_todos(todos: str = "[]") -> str:
        try:
            parsed = json.loads(todos)
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"invalid todos JSON: {exc}"})
        if not isinstance(parsed, list):
            return json.dumps({"error": "todos must be a JSON list of strings"})
        todo_items.clear()
        for item in parsed:
            todo_items.append(str(item))
        return json.dumps({"todos": list(todo_items)})

    return {
        "read_file": _read_file,
        "list_dir": _list_dir,
        "glob": _glob,
        "grep": _grep,
        "find_references": _find_references,
        "read_article": _read_article,
        "list_articles": _list_articles,
        "grep_regulation": _grep_regulation,
        "call_detector": _call_detector,
        "call_validator": _call_validator,
        "write_todos": _write_todos,
    }


def _file_label(file_path: pathlib.Path, sandbox: Sandbox) -> str:
    root = sandbox.roots[0]
    try:
        return file_path.resolve().relative_to(root).as_posix()
    except (OSError, ValueError):
        return file_path.as_posix()


def run_orchestrator(
    *,
    file_path: pathlib.Path,
    regulation: str,
    loop_model: Any,
    detector_model: Any,
    validator_model: Any,
    sandbox: Sandbox,
    regulation_sandbox: Sandbox,
    regulation_docs_dir: pathlib.Path,
    max_iterations: int = 12,
    wall_seconds: float = DEFAULT_WALL_SECONDS_PER_FILE,
) -> OrchestratorRun:
    try:
        regulation_pack = get_regulation_pack(regulation)
    except (ModuleNotFoundError, FileNotFoundError) as exc:
        _LOG.warning("orchestrator: regulation %r not packaged: %s", regulation, exc)
        return OrchestratorRun(exit_reason="unknown_regulation")

    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _LOG.warning("orchestrator: cannot read %s: %s", file_path, exc)
        return OrchestratorRun(exit_reason="file_unreadable")

    text = apply_prompt_ignore_directives(text)
    if text is None:
        return OrchestratorRun(exit_reason="file_ignored")

    chunks = token_chunks(file_path, text, count_tokens=token_counter(detector_model))
    if not chunks:
        return OrchestratorRun(exit_reason="file_ignored")
    consult_log = ChunkConsultLog()
    if chunks:
        consult_log.record(chunks[0].id, chunks[0].text)

    file_label = _file_label(file_path, sandbox)
    target_file_resolved = str(file_path.resolve())

    kept_findings: list[dict[str, Any]] = []
    todos: list[str] = []
    counters = {
        "detector_calls": 0,
        "detector_errors": 0,
        "validator_calls": 0,
        "validator_errors": 0,
        "enrichment_depth": 0,
    }
    state = {"chunk": chunks[0], "snippets": [], "last_snippets": [], "searched": False,
             "detected": set(), "completed": set()}
    _debug_emit(
        {
            "event": "orchestrator_start",
            "file_label": file_label,
            "chunks": len(chunks),
            "chunk_token_sizes": [APPROX_TOKENS(c.text) for c in chunks],
            "first_chunk_id": chunks[0].id if chunks else None,
            "first_chunk_tokens": APPROX_TOKENS(chunks[0].text) if chunks else 0,
        }
    )
    enriched_code_store = EnrichedCodeStore()
    candidates_store = CandidatesStore()

    started = time.monotonic()
    deadline = started + wall_seconds

    def _remaining_seconds() -> float:
        return deadline - time.monotonic()

    detector_impl = build_call_detector_tool(
        detector_model=detector_model,
        candidates_store=candidates_store,
        regulation_pack=regulation_pack,
        remaining_seconds=_remaining_seconds,
    )
    validator_impl = build_call_validator_tool(
        validator_model=validator_model,
        enriched_code_store=enriched_code_store,
        candidates_store=candidates_store,
        file_label_provider=lambda: file_label,
        kept_findings=kept_findings,
        regulation_pack=regulation_pack,
        remaining_seconds=_remaining_seconds,
    )

    tools_map = _build_tools_map(
        regulation=regulation_pack.name,
        sandbox=sandbox,
        regulation_sandbox=regulation_sandbox,
        regulation_docs_dir=regulation_docs_dir,
        consult_log=consult_log,
        enriched_code_store=enriched_code_store,
        target_file_resolved=target_file_resolved,
        target_file_label=file_label,
        detector_impl=detector_impl,
        validator_impl=validator_impl,
        counters=counters,
        todos=todos,
        state=state,
    )

    def _context() -> tuple[str, bool]:
        nonlocal tool_call_count
        pending = [chunk for chunk in chunks if chunk.id not in state["completed"]]
        if not pending:
            return "All chunks have completed detection and validation.", True
        advanced = state["chunk"].id in state["completed"]
        if advanced:
            state["chunk"] = pending[0]
            state["snippets"].clear()
            state["searched"] = False
            counters["enrichment_depth"] = 0
        current = state["chunk"]
        if not any(char.isalpha() or char == "_" for char in current.text):
            tools_map["call_detector"]()
            tool_call_count += 1
            if current.id not in state["completed"]:
                tools_map["call_validator"]()
                tool_call_count += 1
            return _context()
        status = "Validate the existing candidates." if current.id in state["detected"] else ""
        return (
            _initial_user_message(file_path, file_label, [current]) + "\n" + status,
            advanced,
        )

    tool_call_count = 0

    def _on_step(step: dict[str, Any]) -> None:
        nonlocal tool_call_count
        if step.get("kind") == "action":
            tool_call_count += 1

    orchestrator_system = prompts.build_orchestrator_system(
        regulation=regulation_pack.name,
        sample_article_id=regulation_pack.sample_article_id,
    )
    _, exit_reason = run_react_loop(
        model=loop_model,
        system_prompt=orchestrator_system,
        initial_user_message=_context()[0],
        tools_map=tools_map,
        max_iterations=max_iterations,
        wall_seconds=_remaining_seconds(),
        on_step=_on_step,
        get_context=_context,
        is_complete=lambda: len(state["completed"]) == len(chunks),
    )
    elapsed = time.monotonic() - started
    if exit_reason == "budget_exhausted_time":
        _LOG.info(
            "orchestrator: time budget exhausted after %.2fs on %s",
            elapsed,
            file_label,
        )

    # A tool-level model failure with no later success means the file was
    # never fully analyzed; report it as a failure, not a clean pass.
    analysis_incomplete = (
        counters["detector_errors"] and not counters["detector_calls"]
    ) or (counters["validator_errors"] and not counters["validator_calls"])
    if analysis_incomplete or (state["detected"] and len(state["completed"]) < len(chunks)):
        exit_reason = "loop_step_failed"

    return OrchestratorRun(
        kept_findings=kept_findings,
        consult_log=consult_log,
        candidates_store=candidates_store,
        tool_call_count=tool_call_count,
        exit_reason=exit_reason,
        detector_called=counters["detector_calls"] > 0,
        validator_called=counters["validator_calls"] > 0,
        enriched_chunks={state["chunk"].id: state["chunk"].text + "".join(state["snippets"])},
    )
