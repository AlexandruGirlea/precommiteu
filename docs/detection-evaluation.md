---
title: Detection evaluation
nav_order: 12
---

# Detection evaluation

Use this workflow when changing detector prompts, validator context or article
checks. The repository contains reusable evaluation tools and regression
fixtures. Raw model outputs, experiment sources and release evaluation reports
are kept privately.

## Measure the failing stage

1. Fix the cases and expected article labels before comparing implementations.
   Include violations, enabled safeguards, scope boundaries and unrelated code.
   Keep labels and rationales out of model inputs and production decisions.
2. Record the current detector and validator outputs. Distinguish missing
   detector candidates, discarded valid candidates, false alarms, wrong articles
   and runtime errors. Inspect the cited source and explanation as well as the
   score.
3. Test the smallest change supported by those failures. Additional source facts,
   article context or literal-value checks may help, but measure each affected
   adapter before enabling the change. Do not infer a benefit for an untested pack.
4. Compare against the same cases, models and settings. Report each adapter
   separately, including regressions and timing. Reject incomplete runs and
   runtime errors; a higher aggregate score alone is not enough.
5. Check reserved cases after selecting a candidate. If they inform a change,
   identify them as development cases in the report. State whether repeated runs
   or an independent benchmark were used.

Replaying recorded detector candidates isolates a validator change and preserves
detector misses in the score. It does not measure a new detector run. Changes to
detector behavior or shared pipeline components need full before/after runs from
separate checkouts.

## Evaluation tools

Run these scripts from the repository root with the local models installed:

| Script | Purpose |
|---|---|
| `tests/evaluate_ai_act.py` | Run the AI Act fixtures |
| `tests/evaluate_regulations.py` | Run another pack, selected with `--regulation` |
| `tests/compare_regulation_evaluations.py` | Compare complete runs with matching cases and labels |

The evaluators use `--models-dir`, `--fixtures` and `--output`. Use `--fail-fast`
to stop on a runtime error, or `--candidates-from` to replay detector candidates.
Run a script with `--help` for its full options. Fixture code is never executed.
The model evaluations are opt-in; the normal test suite does not launch models.

`--validator-ref` replaces only the validator entry point with a historical
version. The remaining pipeline still comes from the checkout. Use separate
checkouts when other changed files would affect the comparison.

## Keep private evidence with its release

Save new reports and measurements under
`tests/evaluation_results/<version>/<regulation>/<run-id>/`. This directory is
ignored by Git and excluded from release packages. Give each run a new directory;
the evaluators also refuse to overwrite an existing output file. Keep a copy in
a private repository or artifact store, since ignored files are not backed up
by Git.

Preserve model and source hashes, the exact fixtures used, raw responses,
settings, errors and timings. Identify accepted runs and explain why experiments
were rejected. Existing records retain their original paths and contents.

Reuse the scripts for later releases by passing the new fixtures and output
paths. Keep case IDs stable when comparing runs and freeze a copy of each case
set with its results. A reserved case that informed implementation is a
regression case from then on; use new private cases for an independent check.

Keep scores, selected checks and unresolved failures in the release report.
Update this guide when the workflow or evaluation tools change. Later
measurements belong in a new release directory, so an older result cannot be
mistaken for a measurement of the current scanner.
