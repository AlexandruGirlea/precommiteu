---
title: Report reference
nav_order: 7
---

# Report reference

`precommiteu scan` produces up to four report artifacts, plus the scan ledger
that makes the next run incremental. This page is the canonical reference for
their structure. All keys are always present; fields that do not apply are
`null` (stable schema: parse values, never key presence).

| Flag | File | Purpose |
|---|---|---|
| `--json-out` | JSON | Full machine-readable result (this page) |
| `--sarif` | SARIF 2.1.0 | Code-scanning UIs (GitHub code scanning, etc.) |
| `--out` | Markdown | Human summary, suitable as a PR comment |
| `--report` | JSONL | Append-only event ledger (audit/debugging) |
| `--scan-log` | JSON | Scan ledger: what was analysed, so the next run can skip it |

## JSON report structure

```json
{
  "findings":   [ ... ],
  "statuses":   [ ... ],
  "advisories": [ ... ]
}
```

### `findings[]`: confirmed violations

Only findings appear here; each one passed validation. With
`--fail-on-findings`, unsuppressed findings set exit code 1.

| Field | Type | Meaning |
|---|---|---|
| `regulation` | string | Regulation pack that produced the finding (e.g. `"gdpr"`) |
| `source` | `"precommiteu"` \| `"retrieval"` | `precommiteu`: confirmed by the validator model with quoted evidence. `retrieval`: an advisory promoted by the calibrated case-similarity gate |
| `file` | string | Path of the offending file, relative to the scanned root |
| `start_line` / `end_line` | int | Line range of the chunk containing the violation. Single-chunk files span the whole file; `code_evidence` is the precise pointer |
| `probable_article_id` | string | Most likely article, e.g. `"gdpr_art32"`. Detection is the primary signal; the article is a strong hint, not a legal determination |
| `code_evidence` | string \| null | Verbatim code the validator located as proof. `null` on `retrieval`-sourced findings (pattern-matched, no quoted line) |
| `description` | string | What the violation is. Retrieval-promoted findings append `[matches a known violation pattern: <article>, similarity <s>]` |
| `eu_ignore_reason` | string \| null | If suppressed by an inline `precommiteu-ignore: <article> reason="..."` marker, the recorded reason; otherwise `null`. Suppressed findings stay in the report for auditability but never affect the exit code |
| `eu_ignore_source` | `"inline"` \| `"config"` \| null | Where the suppression came from; `null` when not suppressed |

To list every accepted finding and its stated justification, see
[Ignoring code and suppressing findings](suppressions.md).

### `statuses[]`: one entry per regulation scanned

| Field | Type | Meaning |
|---|---|---|
| `regulation` | string | Regulation pack name |
| `status` | `"scanned"` \| `"skipped"` \| `"failed"` | Outcome for this regulation |
| `detail` | string \| null | Human-readable note: an interruption, files that could not be scanned, files reused from the scan ledger |
| `chunks_scanned` | int | Code chunks analyzed |
| `detector_candidates` | int | Raw candidates the detector emitted (before validation) |
| `validator_rejected` | int | Validator-kept results dropped at the final translation checks |

### `advisories[]`: unconfirmed candidates, never blocking

Detector candidates the validator could not confirm, emitted only for files
with no confirmed finding. Advisories never affect the exit code.

| Field | Type | Meaning |
|---|---|---|
| `regulation` | string | Regulation pack name |
| `file` | string | File the candidate refers to |
| `description` | string | The detector's description of the suspected issue |
| `retrieval_verdict` | `"violation_pattern"` \| `"compliant_pattern"` \| `"inconclusive"` \| null | How the candidate compares against the pack's case index; `null` when the pack ships no index |
| `retrieval_confidence` | float \| null | Violation share of the retrieved-neighbor vote, 0..1 |
| `retrieval_similarity` | float \| null | Normalized similarity of the closest known case, 0..1 |
| `retrieval_article_id` | string \| null | Probable article suggested by the neighbor vote (a soft hint, since advisories are for human review) |

## SARIF report

Standard SARIF 2.1.0: one rule per article cited, one `result` per finding.
Suppressed findings carry `properties.eu_ignored: true` and the reason. All
text fields are HTML-escaped. Import it into any SARIF-aware code-scanning
UI.

## Markdown summary (`--out`)

A table of confirmed findings (location, article, evidence, description)
headed `## precommitEU: regulatory scan`. Intended to be posted verbatim as
a PR comment.

## Event ledger (`--report`)

Append-only JSONL, one event per line, each `{"event", "ts", "payload"}`.
Written incrementally and fsync-friendly: a crashed scan leaves a readable
ledger up to the moment of failure.

| `event` | `payload` keys |
|---|---|
| `scan_start` | `files_total`, `regulations` |
| `ledger_loaded` | `regulation`, `path`, `reused`, `to_scan` |
| `file_reused` | `file`, `regulation`, `kept` |
| `detector_adapter` | `regulation`, `adapter` |
| `files_oversized` | `files` |
| `ci_diff_resolved` | `merge_target`, `resolved_ref`, `changed_files` |
| `file_start` | `file`, `regulation`, `chunks` |
| `file_ignored` | `file`, `regulation` |
| `orchestrator_done` | `file`, `regulation`, `route`, `fell_back`, `detector_called`, `validator_called`, `kept_raw`, `tool_calls`, `exit_reason` |
| `finding` | `file` |
| `file_done` | `file`, `regulation`, `kept` |
| `file_error` | `file`, `regulation`, `error` |
| `scan_interrupted` | `files_done`, `files_total` |
| `scan_done` | `findings_total`, `advisories_total`, `files_reused`, `elapsed_ms` |

A full `finding` record (the same object as in `--json-out`) is appended
alongside the `finding` event.

`ledger_loaded` is emitted once per regulation before any model is loaded, and
`file_reused` once per file taken from the scan ledger instead of being
analysed. A reused file emits no `file_start`, `orchestrator_done` or
`file_done`; its findings are still replayed as `finding` records.

### `orchestrator_done`: what happened to one file

One record per file per regulation. This is the only place the analysis
route and its outcome are reported.

| Key | Type | Meaning |
|---|---|---|
| `route` | `"direct"` \| `"orchestrator"` | Which route the file was sent to. See [cli.md](cli.md#analysis-routing---agent-mode) for how `auto` decides |
| `fell_back` | bool | `true` when the orchestrator stopped without reaching the detector and the file was re-scanned on the direct route. The remaining fields then describe that second pass |
| `detector_called` | bool | Whether the detector ran at least once on this file |
| `validator_called` | bool | Whether the validator ran at least once |
| `kept_raw` | int | Findings the validator kept, **before** the article and evidence checks. Always `>=` the file's confirmed finding count |
| `tool_calls` | int | Direct route: detector + validator calls. Orchestrator route: agent steps that invoked a tool (`EMIT` is not counted) |
| `exit_reason` | string | Why analysis of this file stopped, from the table below |

`kept_raw` minus the `kept` in the following `file_done` event is the number
dropped by the evidence and article-registry checks. Set
`PRECOMMITEU_DEBUG_VALIDATOR=1` for the per-candidate drop reason.

### `exit_reason` values

| Value | Route | Meaning | Counts as a failed file? | Recorded in the scan ledger? |
|---|---|---|---|---|
| `direct` | direct | Every chunk was processed normally | No | Yes |
| `emit` | orchestrator | The agent decided it was done and stopped | No | Yes |
| `budget_exhausted_time` | both | The per-file wall clock ran out (`--max-wall-seconds-per-file`) | No | No |
| `budget_exhausted_iters` | orchestrator | The agent used all its steps without stopping (`--max-orchestrator-iterations`) | No | No |
| `direct_partial` | direct | The detector or validator raised on at least one chunk | **Yes** | No |
| `loop_step_failed` | orchestrator | Three consecutive agent steps failed to run or to parse | **Yes** | No |
| `file_ignored` | orchestrator | Ignore directives stripped the whole file | No | No |
| `unknown_regulation` | orchestrator | The regulation pack could not be imported | No | No |
| `file_unreadable` | orchestrator | The file could not be read. Rarely seen: an unreadable file is normally caught earlier and reported as `file_error` | No | No |

Only `direct_partial` and `loop_step_failed` increment the per-regulation
`files_errored` counter, flip that regulation's `status` to `failed`, and
drive exit code 3 under `--fail-on-error` (or `--ci`).

An orchestrator run can stop without ever reaching the detector. Rather than
report that file as clean, the scanner re-scans it on the direct route with
whatever is left of `--max-wall-seconds-per-file` and sets `fell_back` to
`true`.

That recovery is not always possible. A record with `detector_called: false`
is a file that was **not analysed**: it contributes no findings and does not
affect the exit code.

```bash
jq -r 'select(.event == "orchestrator_done")
       | select(.payload.detector_called == false)
       | "\(.payload.file) \(.payload.exit_reason)"' scan-events.jsonl
```

## Scan ledger (`--scan-log`)

State, not a report: the record of which files were analysed, so the next scan
can skip the ones that did not change. See
[Incremental rescans](cli.md#incremental-rescans) for the behaviour; this
section pins the format.

One file per scanned folder and regulation, by default
`~/.precommiteu/scans/<regulation>-<sha256 of the absolute scanned path, first
16 hex chars>.json`. Never inside the scanned folder. Rewritten atomically
after every analysed file, so an interrupted scan keeps everything finished
before it.

```json
{
  "version": 1,
  "regulation": "gdpr",
  "target": "/home/you/work/api",
  "updated_at": "2026-08-17T09:12:44+00:00",
  "files": {
    "src/user_store.py": {
      "size": 4211,
      "mtime_ns": 1755421964123456789,
      "sha256": "6f1c...",
      "scanned_at": "2026-08-17T09:12:44+00:00",
      "findings": [ ... ],
      "advisories": [ ... ]
    }
  }
}
```

| Field | Meaning |
|---|---|
| `version` | Ledger format version. Anything but `1` is ignored and the scan is full |
| `regulation` | The pack these results belong to. A file cleared for GDPR says nothing about another regulation, so a mismatch is ignored |
| `target` | Absolute scanned root. A mismatch is ignored |
| `files` | Keys are file paths relative to `target`, the same labels used in `findings[].file` |
| `size` / `mtime_ns` | The fast path. Both matching means the file is unchanged and is not read |
| `sha256` | Confirms a match when the size or mtime moved. A different digest means a rescan |
| `scanned_at` | When the entry was written, UTC |
| `findings` / `advisories` | The exact objects from `--json-out`, replayed into the next run's reports |

Only files analysed end to end are listed. Entries whose file no longer exists
are dropped on load, so a deleted file disappears from the ledger and from the
results. A missing, unreadable, truncated or foreign ledger is treated as
absent: the scan runs in full, and the scan never fails because of it.
