---
title: Python library
nav_order: 10
---

# Python Library Guide

`precommiteu` is importable as a Python library. The same engine that backs the CLI is exposed through two functions: `scan_paths` (scan files/directories) and `scan_diff` (scan only files changed against a git merge target).

```python
from precommiteu import (
    Advisory,
    Finding,
    GitDiffError,
    ScanResult,
    ScanStatus,
    scan_diff,
    scan_paths,
)
```

Each call to `scan_paths` or `scan_diff` spawns the local inference servers it needs, runs the scan, and shuts the servers down before returning. There is no separate server lifecycle to manage.

## Minimal scan

```python
import os
from precommiteu import scan_paths

os.environ["PRECOMMITEU_MODELS_DIR"] = "/opt/precommiteu/models"

result = scan_paths(["src/"])

print(f"{len(result.findings)} finding(s), {len(result.advisories)} advisory(ies)")
for f in result.findings:
    print(f"{f.file}:{f.start_line}-{f.end_line} [{f.probable_article_id}] {f.description}")
```

`scan_paths` accepts any iterable of `str` or `pathlib.Path` (files or directories). Defaults: the `gdpr` regulation pack, automatic agent routing, models resolved from `PRECOMMITEU_MODELS_DIR`.

## Diff scan (`scan_diff`)

`scan_diff` scans only files added or modified relative to a merge target, resolved via `git diff --name-only --diff-filter=AM <target>...HEAD`.

```python
from precommiteu import GitDiffError, scan_diff

try:
    result = scan_diff(merge_target="main", repo_root=None)  # repo_root defaults to cwd
except GitDiffError as exc:
    # Raised when: cwd is not a git repository, the merge target cannot be
    # resolved (neither "main" nor "origin/main" exists), or git diff fails.
    print(f"diff scan unavailable: {exc}")
    raise SystemExit(2)

if not result.findings:
    print("clean")
```

Merge target resolution order:

| Source | Value |
|---|---|
| `merge_target=` argument | used if not `None` |
| `GIT_MERGE_TARGET_BRANCH` env var | used if argument is `None` |
| Default | `"main"` |

The target is tried as a local ref first, then as `origin/<target>`. If no files changed, `scan_diff` returns immediately with empty findings and a per-regulation `ScanStatus` whose `detail` is `"no files changed vs merge target"`.

`scan_diff` takes every `scan_paths` parameter (see the reference table below) plus `merge_target: str | None = None`. It is keyword-only.

## Consuming results

```python
result = scan_paths(["billing/"], regulations=("gdpr",))

for f in result.findings:
    assert f.source in ("precommiteu", "retrieval")
    print(f.regulation, f.probable_article_id, f.file, f.start_line, f.end_line)
    if f.code_evidence:               # None for retrieval-promoted findings
        print("  evidence:", f.code_evidence)
    if f.eu_ignore_reason:            # finding was suppressed by an eu-ignore marker
        print("  suppressed:", f.eu_ignore_reason, "via", f.eu_ignore_source)

for a in result.advisories:
    print("ADVISORY", a.regulation, a.file, a.description)
    if a.retrieval_verdict is not None:
        print("  retrieval:", a.retrieval_verdict, a.retrieval_confidence,
              a.retrieval_similarity, a.retrieval_article_id)

for s in result.statuses:
    print(s.regulation, s.status, s.detail,
          s.chunks_scanned, s.detector_candidates, s.validator_rejected)
```

All result types are pydantic models; use `result.model_dump()` / `result.model_dump_json()` for serialization.

### `Finding`: confirmed, evidence-backed

| Field | Type | Meaning |
|---|---|---|
| `regulation` | `str` | Regulation pack name (e.g. `"gdpr"`) |
| `source` | `"precommiteu" \| "retrieval"` | `"precommiteu"` = validated by the model with visible evidence; `"retrieval"` = advisory promoted by a high-confidence match against known violation cases |
| `file` | `str \| None` | Repo-relative path |
| `start_line` / `end_line` | `int \| None` | Line range of the hosting code chunk |
| `probable_article_id` | `str \| None` | Article identifier (e.g. `"gdpr_art32"`), checked against the pack's article registry |
| `code_evidence` | `str \| None` | Exact code excerpt proving the finding; `None` for retrieval-promoted findings |
| `description` | `str` | Human-readable explanation |
| `eu_ignore_reason` | `str \| None` | Reason text from a matching suppression marker, if any |
| `eu_ignore_source` | `"inline" \| "config" \| None` | Where the suppression came from |

### `Advisory`: non-blocking candidate

Advisories are detector candidates that did not survive validation. They are emitted per file only when that file produced no confirmed findings.

| Field | Type | Meaning |
|---|---|---|
| `regulation` | `str` | Regulation pack name |
| `file` | `str` | Repo-relative path |
| `description` | `str` | Candidate issue description |
| `retrieval_verdict` | `str \| None` | Case-index verdict (e.g. `"violation_pattern"`); `None` if no case index is packaged for the regulation |
| `retrieval_confidence` | `float \| None` | Verdict confidence |
| `retrieval_similarity` | `float \| None` | Similarity to the matched case |
| `retrieval_article_id` | `str \| None` | Article suggested by the matched case |

An advisory whose retrieval verdict is `"violation_pattern"` and clears the calibrated confidence and similarity thresholds for a known article is promoted to a `Finding` with `source="retrieval"` and does not appear in `advisories`.

### `ScanStatus`: per-regulation outcome

| Field | Type | Meaning |
|---|---|---|
| `regulation` | `str` | Regulation pack name |
| `status` | `"scanned" \| "skipped" \| "failed"` | Outcome |
| `detail` | `str \| None` | e.g. `"interrupted after 3 of 10 files"` after Ctrl-C, or `"no files changed vs merge target"` |
| `chunks_scanned` | `int` | Code chunks processed |
| `detector_candidates` | `int` | Raw candidates produced by the detector |
| `validator_rejected` | `int` | Candidates rejected during validation |

### `ScanResult`

| Field | Type |
|---|---|
| `findings` | `list[Finding]` (deduplicated) |
| `statuses` | `list[ScanStatus]` |
| `advisories` | `list[Advisory]` (defaults to `[]`) |

## Streaming callbacks

Results stream as the scan runs via three optional callbacks. Exceptions raised inside any callback are logged and swallowed; they never abort the scan.

```python
from precommiteu import Advisory, Finding, scan_paths

def on_progress(event: dict) -> None:
    if event["event"] == "file_done":
        print(f"done {event['file']}: {event['kept']} kept")

def on_finding(f: Finding) -> None:
    print(f"FINDING {f.file}:{f.start_line} {f.probable_article_id}")

def on_advisory(a: Advisory) -> None:
    print(f"advisory {a.file}: {a.description}")

result = scan_paths(
    ["src/"],
    on_progress=on_progress,
    on_finding=on_finding,
    on_advisory=on_advisory,
)
```

`on_progress` receives a `dict` whose `"event"` key is one of:

| Event | Extra keys | When |
|---|---|---|
| `scan_start` | `files_total`, `regulations` | After file collection |
| `detector_adapter` | `regulation`, `adapter` | Detector adapter resolved for a regulation |
| `files_oversized` | `files` | Files skipped for exceeding `max_file_bytes` |
| `file_start` | `file`, `regulation`, `chunks` | Before a file is scanned |
| `file_ignored` | `file`, `regulation` | File excluded by an ignore directive |
| `orchestrator_done` | `file`, `regulation`, `route` (`"orchestrator"` or `"direct"`), `detector_called`, `validator_called`, `kept_raw`, `tool_calls`, `exit_reason` | Agent loop finished for a file |
| `finding` | `file` | A confirmed finding was kept |
| `file_done` | `file`, `regulation`, `kept` | File finished |
| `file_error` | `file`, `regulation`, `error` | A file failed; the scan continues |
| `scan_interrupted` | `files_done`, `files_total` | KeyboardInterrupt; partial results are still returned |
| `scan_done` | `findings_total`, `advisories_total`, `elapsed_ms` | Scan finished |
| `ci_diff_resolved` | `merge_target`, `resolved_ref`, `changed_files` | `scan_diff` only, after git diff resolution |

Callback type aliases (`ProgressCallback`, `FindingCallback`, `AdvisoryCallback`) are importable from `precommiteu.scan` for annotations.

## Configuring models

Model bundle layout: one shared `base.gguf` plus one `<regulation>/detector-adapter.gguf` per regulation pack.

```text
/opt/precommiteu/models/
├── base.gguf
└── gdpr/
    └── detector-adapter.gguf
```

Two ways to point the library at it:

```python
# 1. Environment (same mechanism as the CLI's --models-dir)
import os
os.environ["PRECOMMITEU_MODELS_DIR"] = "/opt/precommiteu/models"
result = scan_paths(["src/"])

# 2. Explicit paths, overrides the environment
import pathlib
root = pathlib.Path("/opt/precommiteu/models")
result = scan_paths(
    ["src/"],
    orchestrator_model_path=root / "base.gguf",
    detector_adapter_path=root / "gdpr" / "detector-adapter.gguf",
)
```

Resolution rules:

- `orchestrator_model_path=None` resolves to `$PRECOMMITEU_MODELS_DIR/base.gguf`. If neither is set, `scan_paths` raises `ValueError` with a hint describing the expected layout.
- `detector_adapter_path=None` resolves to `$PRECOMMITEU_MODELS_DIR/<regulation>/detector-adapter.gguf` for the first regulation in `regulations`. If that file does not exist, the scan proceeds with the base model only and logs a degraded-mode warning.
- The validator always runs on the base model resolved above, with the built-in grammar. It takes no adapter and no grammar override.

## Agent mode

```python
result = scan_paths(["src/"], agent_mode="direct")
```

| Value | Behavior |
|---|---|
| `"auto"` (default) | Per file: uses the tool-driven orchestrator when any sibling file's stem (3+ chars, first 200 siblings) appears as a whole word in the file text; otherwise the direct detector/validator path |
| `"direct"` | Always the direct path (no cross-file tool use) |
| `"orchestrator"` | Always the orchestrator loop, sandboxed to the file's directory and the regulation docs |

Any other value raises `ValueError`.

## `scan_paths` parameter reference

All parameters except `paths` are keyword-only. `scan_diff` accepts the same set (minus `paths`, plus `merge_target`).

| Name | Type | Default | Meaning |
|---|---|---|---|
| `paths` | `Iterable[str \| pathlib.Path]` | required | Files and/or directories to scan; test files are skipped |
| `regulations` | `tuple[str, ...]` | `("gdpr",)` | Regulation packs to scan against, in order |
| `orchestrator_model_path` | `pathlib.Path \| None` | `None` | Base model GGUF; `None` = resolve from `PRECOMMITEU_MODELS_DIR` |
| `detector_adapter_path` | `pathlib.Path \| None` | `None` | Detector adapter GGUF; `None` = resolve from models dir, degrade to base-only if absent |
| `detector_grammar_path` | `pathlib.Path \| None` | `None` | Custom GBNF grammar for detector output; `None` = built-in grammar |
| `agent_mode` | `str` | `"auto"` | `"auto"`, `"direct"`, or `"orchestrator"` |
| `n_ctx` | `int` | `32768` | Inference context window |
| `n_gpu_layers` | `int` | `99` | Layers offloaded to GPU (`0` = CPU only) |
| `threads` | `int \| None` | `None` | Inference threads; `None` = server default |
| `max_iterations` | `int` | `12` | Orchestrator loop iteration cap per file |
| `wall_seconds_per_file` | `float` | `90.0` | Wall-clock budget per file |
| `on_progress` | `Callable[[dict], None] \| None` | `None` | Progress event callback |
| `on_finding` | `Callable[[Finding], None] \| None` | `None` | Called for each confirmed finding as it is kept |
| `on_advisory` | `Callable[[Advisory], None] \| None` | `None` | Called for each advisory as it is emitted |
| `repo_root` | `pathlib.Path \| None` | `None` | Root for repo-relative file labels; `None` = cwd. For `scan_diff`, also the git checkout to diff |
| `regulation_docs_dir` | `pathlib.Path \| None` | `None` | Directory of regulation reference docs for the orchestrator; `None` = packaged docs |
| `max_file_bytes` | `int \| None` | `1_000_000` | Per-file size cap; larger files are skipped and reported via `files_oversized`. `None` disables the cap |

Returns: `ScanResult`. Raises: `ValueError` (no model configured, bad `agent_mode`). `scan_diff` additionally raises `GitDiffError`.
