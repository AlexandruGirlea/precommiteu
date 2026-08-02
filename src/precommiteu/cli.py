from __future__ import annotations

import argparse
import importlib
import os
import pathlib
import sys
from contextlib import ExitStack

from precommiteu import __version__
from precommiteu.config import DEFAULT_MAX_ITERATIONS, DEFAULT_WALL_SECONDS_PER_FILE
from precommiteu.defaults import (
    MISSING_MODELS_HINT,
    default_orchestrator_model,
)
from precommiteu.regulations import DEFAULT_REGULATION, get_regulation_pack
from precommiteu.reporting import IncrementalReporter, attach_scan_log, log_scan_event
from precommiteu.scan import (
    GitDiffError,
    _changed_files,
    _require_git_repo,
    _resolve_merge_target,
    scan_diff,
    scan_paths,
)
from precommiteu.src.file_filter import MAX_SCAN_FILE_BYTES, collect_code_files
from precommiteu.src.progress import make_progress_emitter
from precommiteu.src.reporters import jsonl_ledger

DEFAULT_LOG_FILE = "precommiteu_scan.log"

_CI_HELP_EPILOG = """\
CI mode (--ci):
  Scans only the files changed vs a merge-target branch. The scanner reads
  the target branch name from the GIT_MERGE_TARGET_BRANCH environment
  variable (default: "main"). It is intentionally CI-agnostic; the operator
  is expected to wrap it, e.g.

      GIT_MERGE_TARGET_BRANCH=${GITHUB_BASE_REF:-main} \\
          precommiteu scan --ci

  precommiteu does NOT read GITHUB_BASE_REF, CI_MERGE_REQUEST_TARGET_*,
  SYSTEM_PULLREQUEST_TARGETBRANCH, or any other CI-platform-specific env
  var. Wire them through GIT_MERGE_TARGET_BRANCH in your CI config.
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="precommiteu",
        description="Local-first EU regulatory compliance scanner for source code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_CI_HELP_EPILOG,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=False)

    scan = sub.add_parser(
        "scan",
        help="Scan paths for regulatory violations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_CI_HELP_EPILOG,
    )
    scan.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to scan. Omit when using --ci.",
    )
    scan.add_argument(
        "--ci",
        action="store_true",
        help=(
            "CI mode: scan only files changed vs the merge-target branch "
            "named by $GIT_MERGE_TARGET_BRANCH (default: 'main'). "
            "Mutually exclusive with positional paths."
        ),
    )
    scan.add_argument(
        "--regulations",
        default=DEFAULT_REGULATION,
        help=(
            "Comma-separated regulation packs to run "
            f"(default: {DEFAULT_REGULATION!r}). Each name must resolve to "
            "a packaged regulation in precommiteu.regulations."
        ),
    )
    scan.add_argument(
        "--models-dir",
        type=pathlib.Path,
        default=None,
        help="Directory holding the model files (base.gguf, "
        "<regulation>/detector-adapter.gguf). Overrides $PRECOMMITEU_MODELS_DIR.",
    )
    scan.add_argument(
        "--orchestrator-model",
        type=pathlib.Path,
        default=None,
        help="Base GGUF used by the orchestrator deep-agent and validator "
        "(default: base.gguf under --models-dir / $PRECOMMITEU_MODELS_DIR).",
    )
    scan.add_argument(
        "--detector-adapter",
        type=pathlib.Path,
        default=None,
        help="LoRA adapter GGUF applied to the detector llama-server "
        "(default: <regulation>/detector-adapter.gguf under --models-dir / "
        "$PRECOMMITEU_MODELS_DIR).",
    )
    scan.add_argument(
        "--detector-grammar",
        type=pathlib.Path,
        default=None,
        help="Optional GBNF grammar file overriding the built-in detector "
        "output grammar.",
    )
    scan.add_argument(
        "--agent-mode",
        choices=("auto", "direct", "orchestrator"),
        default="auto",
        help="Per-file analysis route: 'direct' = fast two-call scan, "
        "'orchestrator' = context-gathering agent, 'auto' (default) = direct "
        "unless the file references sibling files.",
    )
    scan.add_argument(
        "--gpu-layers",
        type=int,
        default=99,
        help="Model layers offloaded to the GPU (default: 99 = all; 0 = CPU only).",
    )
    scan.add_argument(
        "--threads",
        type=int,
        default=None,
        help="CPU threads for inference (default: auto).",
    )
    scan.add_argument(
        "--n-ctx",
        type=int,
        default=32768,
        help="Model context window in tokens; lower values reduce memory "
        "use (default: 32768).",
    )
    scan.add_argument(
        "--json-out",
        type=pathlib.Path,
        default=None,
        help="Write the full machine-readable result (findings, advisories, "
        "statuses) as JSON.",
    )
    scan.add_argument(
        "--report",
        type=pathlib.Path,
        default=None,
        help="Write a JSONL event ledger of the scan (progress events and "
        "findings, for audit/debugging).",
    )
    scan.add_argument(
        "--sarif",
        type=pathlib.Path,
        default=None,
        help="Write a SARIF 2.1.0 report for code-scanning UIs.",
    )
    scan.add_argument(
        "--out",
        type=pathlib.Path,
        default=None,
        help="Write a markdown summary suitable for a PR comment.",
    )
    scan.add_argument(
        "--log-file",
        type=pathlib.Path,
        default=None,
        help="Append a timestamped scan log (progress events, warnings, errors) "
        f"to this file (default: {DEFAULT_LOG_FILE}).",
    )
    scan.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output files instead of refusing to run.",
    )
    scan.add_argument(
        "--progress",
        choices=("text", "jsonl", "none"),
        default="text",
        help="Progress output on stderr (default: text).",
    )
    scan.add_argument(
        "--max-orchestrator-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help="Maximum agent steps per file (default: 12).",
    )
    scan.add_argument(
        "--max-wall-seconds-per-file",
        type=int,
        default=int(DEFAULT_WALL_SECONDS_PER_FILE),
        help="Wall-clock budget per file in seconds (default: 90).",
    )
    scan.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit 1 when confirmed findings remain after ignore filtering. "
        "Advisories never affect the exit code.",
    )
    scan.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit 3 when any file could not be scanned (results incomplete). "
        "Enabled automatically under --ci so an incomplete scan never reports a "
        "clean pass.",
    )
    scan.add_argument(
        "--show-advisories",
        action="store_true",
        help="Print unconfirmed detector candidates (informational; advisories "
        "never affect the exit code).",
    )
    scan.add_argument(
        "--max-file-bytes",
        type=int,
        default=MAX_SCAN_FILE_BYTES,
        help="Skip files larger than this (default: %(default)s bytes; 0 = no limit).",
    )
    scan.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the files that would be scanned and exit without loading "
        "any model.",
    )

    sub.add_parser(
        "this",
        aliases=["philosophy"],
        help="Print the Zen of EU Code, the project philosophy.",
    )

    return parser


def _parse_regulations(value: str) -> tuple[str, ...]:
    regs = tuple(r.strip() for r in (value or "").split(",") if r.strip())
    if not regs:
        regs = (DEFAULT_REGULATION,)
    for r in regs:
        try:
            get_regulation_pack(r)
        except (ModuleNotFoundError, FileNotFoundError):
            print(
                f"error: regulation '{r}' not packaged in precommiteu.regulations",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
    return regs


def _check_output_paths(args: argparse.Namespace) -> str | None:
    # Only paths the user typed are protected; the default log is ours and
    # is opened append-only, so repeat scans in one directory keep working.
    named = [
        ("--json-out", args.json_out),
        ("--report", args.report),
        ("--sarif", args.sarif),
        ("--out", args.out),
        ("--log-file", args.log_file),
    ]
    for flag, path in named:
        if path is not None and pathlib.Path(path).exists():
            return (
                f"error: {flag} target already exists: {path}\n"
                "       precommiteu never overwrites your files; pass a "
                "different path, delete it, or re-run with --force."
            )
    return None


def _run_scan(args: argparse.Namespace) -> int:
    if not args.force:
        clash = _check_output_paths(args)
        if clash is not None:
            print(clash, file=sys.stderr)
            return 2
    if args.log_file is None:
        args.log_file = pathlib.Path(DEFAULT_LOG_FILE)

    regulations = _parse_regulations(args.regulations)

    orchestrator_model = args.orchestrator_model or default_orchestrator_model(
        args.models_dir
    )
    detector_grammar = args.detector_grammar
    if orchestrator_model is None:
        print(f"error: no model paths configured; {MISSING_MODELS_HINT}", file=sys.stderr)
        return 2
    required_paths = [orchestrator_model]
    if detector_grammar is not None:
        required_paths.append(detector_grammar)
    for required in required_paths:
        if not pathlib.Path(required).exists():
            print(f"error: required path not found: {required}", file=sys.stderr)
            return 2

    adapter_path: pathlib.Path | None = args.detector_adapter
    if adapter_path is not None:
        if len(regulations) > 1:
            print(
                "error: a single --detector-adapter can't be combined with "
                "multiple regulations; omit it to auto-resolve per regulation",
                file=sys.stderr,
            )
            return 2
        if not pathlib.Path(adapter_path).exists():
            print(
                f"::warning::precommiteu: detector adapter missing ({adapter_path}); "
                "running without a LoRA-bound detector (degraded mode).",
                file=sys.stderr,
            )
            adapter_path = None

    attach_scan_log(args.log_file)
    log_scan_event(
        {
            "event": "run_start",
            "ci": args.ci,
            "paths": [str(p) for p in args.paths],
            "regulations": list(regulations),
            "orchestrator_model": str(orchestrator_model),
            "detector_adapter": str(adapter_path) if adapter_path is not None else None,
            "detector_grammar": str(detector_grammar) if detector_grammar else "embedded",
            "json_out": str(args.json_out) if args.json_out is not None else None,
            "sarif": str(args.sarif) if args.sarif is not None else None,
            "out": str(args.out) if args.out is not None else None,
            "report": str(args.report) if args.report is not None else None,
        }
    )

    def _finish(code: int) -> int:
        log_scan_event({"event": "run_end", "exit_code": code})
        return code

    output_files = [
        str(p) for p in (args.json_out, args.sarif, args.out, args.report) if p is not None
    ]

    def _print_interrupted() -> None:
        where = f"; partial results written to {', '.join(output_files)}" if output_files else ""
        print(f"precommiteu: scan interrupted{where}", file=sys.stderr)

    reporter = IncrementalReporter(json_out=args.json_out, sarif=args.sarif, out=args.out)
    reporter.snapshot()

    progress_emitter = make_progress_emitter(args.progress)
    interrupted = False

    with ExitStack() as stack:
        ledger = None
        if args.report is not None:
            ledger = stack.enter_context(jsonl_ledger(args.report))

        def _on_progress(payload: dict) -> None:
            nonlocal interrupted
            event = payload.get("event", "progress")
            if event == "scan_interrupted":
                interrupted = True
            if progress_emitter is not None:
                progress_emitter(payload)
            if ledger is not None:
                ledger.write(
                    event,
                    **{k: v for k, v in payload.items() if k != "event"},
                )
            log_scan_event(payload)
            if event in ("file_done", "file_error"):
                reporter.snapshot()

        def _on_finding(f) -> None:
            if ledger is not None:
                ledger.write("finding", finding=f.model_dump(mode="json"))
            reporter.add_finding(f)
            reporter.snapshot()

        def _on_advisory(advisory) -> None:
            reporter.add_advisory(advisory)

        try:
            if args.ci:
                result = scan_diff(
                    regulations=regulations,
                    orchestrator_model_path=orchestrator_model,
                    detector_adapter_path=adapter_path,
                    detector_grammar_path=detector_grammar,
                    agent_mode=args.agent_mode,
                    n_ctx=args.n_ctx,
                    n_gpu_layers=args.gpu_layers,
                    threads=args.threads,
                    max_iterations=args.max_orchestrator_iterations,
                    wall_seconds_per_file=float(args.max_wall_seconds_per_file),
                    on_progress=_on_progress,
                    on_finding=_on_finding,
                    on_advisory=_on_advisory,
                    max_file_bytes=args.max_file_bytes if args.max_file_bytes > 0 else None,
                )
            else:
                result = scan_paths(
                    args.paths,
                    regulations=regulations,
                    orchestrator_model_path=orchestrator_model,
                    detector_adapter_path=adapter_path,
                    detector_grammar_path=detector_grammar,
                    agent_mode=args.agent_mode,
                    n_ctx=args.n_ctx,
                    n_gpu_layers=args.gpu_layers,
                    threads=args.threads,
                    max_iterations=args.max_orchestrator_iterations,
                    wall_seconds_per_file=float(args.max_wall_seconds_per_file),
                    on_progress=_on_progress,
                    on_finding=_on_finding,
                    on_advisory=_on_advisory,
                    max_file_bytes=args.max_file_bytes if args.max_file_bytes > 0 else None,
                )
        except GitDiffError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return _finish(2)
        except RuntimeError as exc:
            print(f"error: scan wiring failed: {exc}", file=sys.stderr)
            return _finish(2)
        except KeyboardInterrupt:
            reporter.snapshot()
            _print_interrupted()
            log_scan_event({"event": "scan_interrupted"})
            return _finish(130)

    reporter.finalize(result)

    visible_findings = [f for f in result.findings if f.eu_ignore_reason is None]
    if visible_findings:
        print(f"\nFindings: {len(visible_findings)}")
        for f in visible_findings:
            location = f.file or "<unknown>"
            if f.start_line:
                location += f":{f.start_line}"
            print(f"  [{f.regulation}] {location} {f.probable_article_id or ''}")
            print(f"      {f.description}")
    else:
        print("\nNo findings.")

    if args.show_advisories and result.advisories:
        print(f"\nAdvisories (unconfirmed, non-blocking): {len(result.advisories)}")
        for advisory in result.advisories:
            print(f"  [{advisory.regulation}] {advisory.file}: {advisory.description}")

    errored = [s for s in result.statuses if s.status == "failed"]
    if errored:
        summary = "; ".join(
            f"{s.regulation}: {s.detail}" if s.detail else s.regulation
            for s in errored
        )
        print(
            f"\nwarning: scan incomplete: {summary}. Results may be missing "
            "findings.",
            file=sys.stderr,
        )

    if interrupted:
        _print_interrupted()
        return _finish(130)
    if (args.fail_on_error or args.ci) and errored:
        return _finish(3)
    if args.fail_on_findings and visible_findings:
        return _finish(1)
    return _finish(0)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command in ("this", "philosophy"):
        importlib.import_module("precommiteu.this")
        return 0

    if args.command != "scan":
        parser.print_help()
        return 0

    if args.ci and args.paths:
        print(
            "error: --ci derives paths from `git diff`; do not pass "
            "positional paths in CI mode.",
            file=sys.stderr,
        )
        return 2
    if not args.ci and not args.paths:
        print(
            "error: scan requires either positional paths or --ci.",
            file=sys.stderr,
        )
        return 2

    if args.dry_run:
        repo_root = pathlib.Path.cwd().resolve()
        if args.ci:
            try:
                _require_git_repo(repo_root)
                target = os.environ.get("GIT_MERGE_TARGET_BRANCH", "main")
                ref = _resolve_merge_target(target, repo_root)
                paths = _changed_files(ref, repo_root)
            except GitDiffError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
        else:
            paths = [pathlib.Path(p) for p in args.paths]

        selected, _oversized = collect_code_files(
            paths,
            repo_root,
            max_bytes=args.max_file_bytes if args.max_file_bytes > 0 else None,
        )
        for path in selected:
            print(str(path))
        return 0

    return _run_scan(args)


if __name__ == "__main__":
    raise SystemExit(main())
