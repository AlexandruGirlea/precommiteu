---
title: CLI reference
nav_order: 3
---

# precommiteu CLI

```sh
precommiteu scan src/ --fail-on-findings --sarif findings.sarif
```

`precommiteu` is a local-first EU regulatory compliance scanner for source code. All inference runs on your machine; no source code leaves it. `scan` carries every flag; `ui` opens a local web interface over the same scanner.

```sh
precommiteu --version
precommiteu scan --help
precommiteu ui --help
```

## The local UI: `precommiteu ui`

```sh
pip install "precommiteu[ui]"
precommiteu ui
```

Starts a loopback server on port 8787 and opens a browser. Nothing is scanned
until you choose a folder in the UI. From there you can install what is missing,
download a regulation pack, run a scan and read the findings. One pack is active
at a time.

| Flag | Meaning |
|---|---|
| `--port N` | Serve on another port (default `8787`). |
| `--no-browser` | Do not open a browser window. |

The extra pulls `fastapi`, `uvicorn` and `huggingface_hub`; a plain
`pip install precommiteu` for CI stays unaffected.

## Flag reference: `precommiteu scan`

| Flag | Expects | Default | Purpose |
| --- | --- | --- | --- |
| `paths` (positional) | one or more files/directories | none | What to scan. Omit when using `--ci`. |
| `--ci` | flag | off | Scan only files changed vs the merge-target branch named by `$GIT_MERGE_TARGET_BRANCH` (default `main`). Mutually exclusive with positional paths. |
| `--regulations` | comma-separated pack names | `gdpr` | Regulation packs to run. Each name must resolve to an installed regulation pack. |
| `--models-dir` | directory path | unset | Directory holding the model files (`base.gguf`, `<regulation>/detector-adapter.gguf`). Overrides `$PRECOMMITEU_MODELS_DIR`. |
| `--orchestrator-model` | GGUF file path | `base.gguf` under the models dir | Base model used by the orchestrator deep-agent and validator. |
| `--detector-adapter` | GGUF file path | `<regulation>/detector-adapter.gguf` under the models dir | LoRA adapter applied to the detector server. |
| `--detector-grammar` | GBNF file path | built-in grammar | Pins the output grammar for the detector call (expert). |
| `--agent-mode` | `auto` \| `direct` \| `orchestrator` | `auto` | Per-file analysis route. `auto` = direct unless the file references sibling files. |
| `--gpu-layers` | integer | `99` | Model layers offloaded to the GPU (`99` = all, `0` = CPU only). |
| `--threads` | integer | auto | CPU threads for inference. |
| `--n-ctx` | integer (tokens) | `32768` | Model context window. Lower values reduce memory use. |
| `--json-out` | file path | unset | Write the full machine-readable result (findings, advisories, statuses) as JSON. |
| `--report` | file path | unset | Write a JSONL event ledger of the scan (progress events and findings, for audit/debugging). |
| `--sarif` | file path | unset | Write a SARIF 2.1.0 report for code-scanning UIs. |
| `--out` | file path | unset | Write a markdown summary suitable for a PR comment. |
| `--log-file` | file path | `precommiteu_scan.log` | Append a timestamped scan log (progress events, warnings, errors). |
| `--progress` | `text` \| `jsonl` \| `none` | `text` | Progress output on stderr. |
| `--max-orchestrator-iterations` | integer | `12` | Maximum agent steps per file. |
| `--max-wall-seconds-per-file` | integer (seconds) | `90` | Wall-clock budget per file. |
| `--fail-on-findings` | flag | off | Exit 1 when confirmed findings remain after ignore filtering. Advisories never affect the exit code. |
| `--fail-on-error` | flag | off (on under `--ci`) | Exit 3 when any file could not be scanned, so an incomplete scan never reports a clean pass. |
| `--show-advisories` | flag | off | Print unconfirmed detector candidates (informational, never blocking). |
| `--max-file-bytes` | integer (bytes) | `1000000` | Skip files larger than this (`0` = no limit). |
| `--rescan-all` | flag | off | Ignore the scan ledger and analyse every selected file, rewriting its ledger entry. See [Incremental rescans](#incremental-rescans). |
| `--scan-log` | file path | `~/.precommiteu/scans/<regulation>-<hash>.json` | Where the scan ledger of analysed files is kept. One regulation per ledger. |
| `--force` | flag | off | Overwrite existing output files instead of refusing to run. See [Never overwriting your files](#never-overwriting-your-files). |
| `--dry-run` | flag | off | Print the files that would be scanned and exit without loading any model. |

## Basic scans

Scan one path:

```sh
precommiteu scan src/
```

Scan multiple paths (files and directories mix freely):

```sh
precommiteu scan src/ api/handlers.py infra/main.tf
```

Preview the file selection without loading any model:

```sh
precommiteu scan src/ --dry-run
```

`--dry-run` prints exactly the files a real scan would process, after all filtering: only recognized source files are selected; test files, documentation, generated files, binaries, dependency directories, files over `--max-file-bytes`, and anything matched by `.eu-ignore` are skipped.

Scan with a different regulation pack, or several at once:

```sh
precommiteu scan src/ --regulations gdpr
precommiteu scan src/ --regulations gdpr,dora
```

CI mode, scan only the files changed vs a merge-target branch:

```sh
GIT_MERGE_TARGET_BRANCH=${GITHUB_BASE_REF:-main} precommiteu scan --ci --fail-on-findings
```

`--ci` is CI-platform-agnostic: it reads only `$GIT_MERGE_TARGET_BRANCH` (default `main`), resolves it locally or as `origin/<branch>`, and scans files added or modified in `git diff <target>...HEAD`. Wire your CI platform's variable through `GIT_MERGE_TARGET_BRANCH` yourself. Passing positional paths together with `--ci` is an error.

## Incremental rescans

A scan records every file it analysed cleanly. The next scan of the same folder
with the same regulation skips the files whose bytes did not change and replays
their results from that record, so a repository that took hours the first time
takes minutes when a handful of files moved.

```sh
precommiteu scan src/     # first run: analyses everything
precommiteu scan src/     # later run: only what changed
```

```
Reused 143 unchanged file(s) for gdpr from /home/you/.precommiteu/scans/gdpr-4f1c9ab2e7d05631.json
```

Reused files are reported as reused, never as analysed again: each emits a
`file_reused` progress event, adds nothing to `chunks_scanned`, and the
regulation's `detail` in `--json-out` says how many were reused. Their findings
and advisories are replayed into every report, so an incremental run still
produces a complete one.

**Where the record lives.** `~/.precommiteu/scans/<regulation>-<hash>.json`,
one file per scanned folder and regulation, named from a hash of the absolute
path so two projects never collide. Nothing is written into the folder being
scanned. `--scan-log PATH` puts it wherever you want, including inside the
repository if that is your choice.

**What counts as analysed.** Only a file the scanner took end to end. Anything
that ran out of per-file budget, errored, or was cut short by Ctrl-C is left
out of the ledger and analysed again next time.

| Situation | Next run |
| --- | --- |
| Same bytes | Reused |
| Content changed | Rescanned |
| mtime changed but bytes identical (checkout, touch, cloud sync) | Reused, after a sha256 confirms it |
| Budget exhausted, error or interrupt last time | Rescanned |
| File deleted | Dropped from the ledger and from the results |
| No ledger, unreadable ledger, or a ledger for another regulation or folder | Full scan |

Change detection is size plus mtime first, and a sha256 whenever either
differs. A `git checkout` that rewrites every timestamp therefore costs one
hash per file instead of a full rescan, and the ledger records the new
timestamps so the next run is back on the fast path.

Force a complete pass, for example after upgrading the model bundle:

```sh
precommiteu scan src/ --rescan-all
```

`--ci` keeps no ledger: it already scans only what changed against the merge
target, and CI runners are meant to carry no state between runs. Passing
`--rescan-all` or `--scan-log` together with `--ci` is an error.

## Output reports

All four report flags can be combined in one run; each writes a different artifact:

```sh
precommiteu scan src/ \
  --json-out result.json \
  --sarif findings.sarif \
  --out pr-comment.md \
  --report scan-events.jsonl \
  --log-file scan.log
```

| Flag | Format | Contents | Write behavior |
| --- | --- | --- | --- |
| `--json-out` | JSON | Complete result: `findings` (including suppressed ones, with `eu_ignore_reason` / `eu_ignore_source` set), `statuses` (per-regulation counters: `chunks_scanned`, `detector_candidates`, `validator_rejected`), `advisories` (with retrieval annotation fields) | Snapshot, rewritten atomically after every file and finding, so partial results survive an interrupted scan |
| `--sarif` | SARIF 2.1.0 | Findings only, and only those whose cited article resolves in the regulation pack's article registry. One SARIF rule per article id with a `helpUri` link to the article text. Suppressed findings carry `properties.eu_ignored` and `properties.eu_ignore_reason`. Advisories are not included | Snapshot, rewritten atomically during the scan |
| `--out` | Markdown | PR-comment summary: finding count per regulation and a table `Location \| Article \| Evidence \| Description`, with article links and the code evidence inlined (truncated to 120 chars). Findings only | Snapshot, rewritten atomically during the scan |
| `--report` | JSONL | Chronological event ledger: one record per line (`{"event", "ts", "payload"}`) for every progress event (`scan_start`, `file_start`, `orchestrator_done`, `file_done`, `file_error`, `scan_done`, ...) plus a full `finding` record per finding. Each line is flushed and fsynced | Append-only stream; never overwrites previous runs |
| `--log-file` | Plain text | Timestamped human-readable log of the same events plus warnings and errors. If the file cannot be opened, the scan warns and continues | Appended; written by default to `precommiteu_scan.log` |

In short: `--json-out` is the final state document, `--report` is the audit trail of how the scan got there, `--log-file` is the operator log, and `--sarif` / `--out` are presentation formats for code-scanning UIs and PR comments respectively.

### Never overwriting your files

precommitEU refuses to write over a file that is already there. If any path you pass to `--json-out`, `--report`, `--sarif`, `--out` or `--log-file` already exists, the scan stops with exit code 2 **before a single model is loaded**, and nothing on disk is touched:

```
$ precommiteu scan src/ --json-out result.json
error: --json-out target already exists: result.json
       precommiteu never overwrites your files; pass a different path, delete it, or re-run with --force.
```

Three exceptions:

| Case | Behavior |
| --- | --- |
| `--force` | Existing targets are overwritten |
| `--log-file` left at its default | Never blocks a scan. `precommiteu_scan.log` is opened append-only. Pass `--log-file` explicitly and it *is* guarded |
| `--dry-run` | Guard is skipped; a dry run writes no report files |

Snapshot reports (`--json-out`, `--sarif`, `--out`) are written by staging a `<name>.precommiteu_tmp_<pid>` sibling and atomically renaming it into place. A file of your own that happens to end in `.tmp` is never disturbed.

In CI, prefer a fresh path per run, or add `--force`:

```sh
precommiteu scan --ci --sarif findings.sarif --force
```

Progress on stderr is independent of the report files:

```sh
precommiteu scan src/ --progress jsonl   # machine-readable progress on stderr
precommiteu scan src/ --progress none    # silent
```

## Findings vs advisories

A **finding** is a confirmed, evidence-backed result: the validator confirmed the candidate, cited a known article from the regulation pack, and quoted code evidence that is actually visible in the analyzed text. Findings drive the exit code (with `--fail-on-findings`) and appear in all report formats.

An **advisory** is an unconfirmed detector candidate: the detector flagged it, but validation did not confirm it. Advisories are informational, never affect the exit code, and are only emitted for files that produced no confirmed finding.

```sh
precommiteu scan src/ --show-advisories
```

```
Advisories (unconfirmed, non-blocking): 2
  [gdpr] src/export.py: Bulk export of user records without consent check
  [gdpr] src/jobs/cleanup.py: Retention period not enforced before deletion
```

When the regulation pack ships a case index (`cases.jsonl`), each advisory is additionally scored against known violation patterns. The annotation fields appear on the advisory in `--json-out`:

| Field | Meaning |
| --- | --- |
| `retrieval_verdict` | Pattern-match verdict (e.g. `violation_pattern`) |
| `retrieval_confidence` | Confidence of the verdict |
| `retrieval_similarity` | Similarity to the closest known case |
| `retrieval_article_id` | Article suggested by the matched cases |

An advisory whose verdict is `violation_pattern` at calibrated confidence and similarity thresholds, citing an article known to the pack, is promoted to a confirmed finding with `source: "retrieval"` and a description suffix noting the matched article and similarity. All other advisories stay non-blocking.

## Analysis routing: `--agent-mode`

```sh
precommiteu scan src/ --agent-mode direct        # fastest: fixed two-call scan per file
precommiteu scan src/ --agent-mode orchestrator  # deepest: context-gathering agent per file
precommiteu scan src/                             # auto (default)
```

| Mode | Behavior |
| --- | --- |
| `direct` | Fixed detector + validator pass over the file's chunks. No tool use. |
| `orchestrator` | A context-gathering agent that can read neighboring files (sandboxed to the scanned file's directory) and consult regulation texts before deciding. Bounded by `--max-orchestrator-iterations` and `--max-wall-seconds-per-file`. |
| `auto` | `direct`, escalating to `orchestrator` per file only when the file references sibling files. |

Escalation in `auto` mode is purely structural: the scanner lists the other file stems in the same directory (stems of 3+ characters, first 200 siblings) and escalates when any sibling stem appears as a whole word anywhere in the file text. A file that never mentions a sibling file stays on the direct route.

## Model selection

The scanner needs the precommitEU model bundle (see [install.md](install.md)): one shared `base.gguf` plus one `detector-adapter.gguf` per regulation.

```
<models-dir>/
  base.gguf
  gdpr/
    detector-adapter.gguf
```

Point the scanner at it either way:

```sh
export PRECOMMITEU_MODELS_DIR=/opt/precommiteu/models
precommiteu scan src/

# or per invocation (overrides the env var):
precommiteu scan src/ --models-dir /opt/precommiteu/models
```

Resolution order: explicit file flags > `--models-dir` > `$PRECOMMITEU_MODELS_DIR`. Explicit paths bypass the directory layout entirely:

```sh
precommiteu scan src/ \
  --orchestrator-model /opt/models/base.gguf \
  --detector-adapter /opt/models/gdpr/detector-adapter.gguf
```

Failure behavior: a missing base model is a hard error (exit 2). A missing detector adapter is not: the scan continues on the base model alone and prints a `::warning::` marking the run as degraded mode.

Expert flags (not needed in normal operation):

```sh
# Pin a custom detector output grammar instead of the built-in one
precommiteu scan src/ --detector-grammar custom-detector.gbnf
```

The validator always runs on the base model with the built-in grammar and takes no adapter.

## Performance tuning

```sh
# CPU-only host, pinned thread count
precommiteu scan src/ --gpu-layers 0 --threads 8

# Smaller context window for memory-constrained machines
precommiteu scan src/ --n-ctx 16384

# Tighter per-file budgets for large repos
precommiteu scan src/ --max-wall-seconds-per-file 45 --max-orchestrator-iterations 6

# Raise or remove the file-size cutoff (0 = no limit)
precommiteu scan src/ --max-file-bytes 0
```

| Flag | Effect |
| --- | --- |
| `--gpu-layers` | Layers offloaded to GPU. `99` (default) offloads everything; `0` forces CPU-only inference. |
| `--threads` | CPU inference threads. Default lets the runtime auto-select. |
| `--n-ctx` | Context window in tokens (default 32768). Lower values reduce memory use. |
| `--max-file-bytes` | Files above this size are skipped and reported in a `files_oversized` progress event (default 1000000; `0` disables the limit). |
| `--max-wall-seconds-per-file` | Hard wall-clock budget per file (default 90 s). |
| `--max-orchestrator-iterations` | Cap on agent steps per file in orchestrator routing (default 12). |

## Exit codes

```sh
precommiteu scan src/ --fail-on-findings
echo $?
```

| Code | Meaning |
| --- | --- |
| `0` | Scan completed. Either no visible findings, or findings present but `--fail-on-findings` was not set. Also returned by `--dry-run` and bare `precommiteu` (help). |
| `1` | `--fail-on-findings` was set and at least one confirmed finding remains after suppression filtering. Advisories and suppressed findings never trigger exit 1. |
| `2` | Usage or configuration error: unknown regulation pack, no model paths configured, a required model/grammar file missing, an output target that already exists (see [Never overwriting your files](#never-overwriting-your-files)), `--ci` combined with positional paths, neither paths nor `--ci` given, or a git error in CI mode. |
| `3` | Scan incomplete: one or more files could not be analyzed (model server failure, unreadable file, budget exhausted mid-analysis) and `--fail-on-error` was in effect (always on under `--ci`). The affected regulation's status is `failed` in `--json-out`; a warning summarizing the errors is printed to stderr. |
| `130` | Scan interrupted (Ctrl-C). Partial results are preserved in any `--json-out` / `--sarif` / `--out` files written so far. |
## Suppressions

Three mechanisms, in increasing order of auditability:

| Mechanism | Effect | Leaves a record |
|---|---|---|
| `.eu-ignore` file | Excludes paths during discovery, so they are never read | No |
| Inline `eu-ignore` directives | Blanks source lines before the model sees them, preserving line numbers | No |
| `precommiteu-ignore: <article> reason="..."` markers | Suppresses a confirmed finding and records your reason | Yes, in JSON and SARIF |

Suppressed findings are removed from console output and from the
`--fail-on-findings` exit-code check. Only the marker form keeps an entry in
`--json-out` and SARIF.

See [Ignoring code and suppressing findings](suppressions.md) for the full
syntax, matching rules and audit workflow.
