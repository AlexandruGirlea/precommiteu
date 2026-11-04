---
title: Detection evaluation
nav_order: 12
---

# Detection evaluation

## Version 0.3 results

On 3 November 2026, a built 0.3.0 wheel was evaluated with the released
v0.3.0 model bundle: Qwen2.5-Coder-7B-Instruct Q4_K_M plus detector adapters,
and Qwen3.6-35B-A3B IQ4_XS for validation. The 450 case runs contain 225
positive and 225 clean examples, drawn from nine synthetic golden datasets.
There are 440 unique code snippets; the combined and standalone CRA, DMA and
NIS2 datasets overlap. Advisories are excluded.

| Dataset | True positives | True negatives | False positives | Misses | Errors |
|---|---|---|---|---|---|
| GDPR | 23 | 23 | 2 | 2 | 0 |
| EU AI Act | 16 | 24 | 1 | 9 | 0 |
| EU Data Act | 23 | 24 | 1 | 2 | 0 |
| DORA | 22 | 24 | 1 | 3 | 0 |
| DSA | 23 | 25 | 0 | 2 | 0 |
| CRA/DMA/NIS2 combined | 22 | 25 | 0 | 3 | 0 |
| CRA | 21 | 24 | 1 | 4 | 0 |
| DMA | 22 | 24 | 1 | 2 | 1 |
| NIS2 | 20 | 23 | 2 | 5 | 0 |
| Total | 192 | 216 | 9 | 32 | 1 |

- Case-level precision: 192/201 flagged cases, **95.5%**.
- Recall: 192/224 completed positive cases, **85.7%**; **85.3%** if the
  incomplete positive case counts as a miss.
- False-positive rate: 9/225 clean cases, **4%**. The false-alarm share among
  flagged cases is 9/201, **4.5%**; these are different denominators.
- F1 on completed cases: **90.4%**. Accuracy across all attempts: 408/450,
  **90.7%**, with the error counted as unsuccessful.
- Exact article-set matches: 356/450, **79.1%**, including clean cases.
  Of 192 detected positive cases, 52 had incomplete or different article sets.
- 449/450 scans completed. One DMA case exhausted the validator output-token
  limit and was marked incomplete, not clean.

These are file-level yes/no detection metrics, not a judgment that every
finding or legal citation is correct. All cases took the direct route;
cross-file reasoning and CI diff selection were outside this evaluation.
The run used a 32 GiB Apple Silicon Mac, llama.cpp build 10450, a 32768-token
context, a 300-second file budget and no incremental reuse. It took about
66 minutes. The archived wheel and source snapshot identify the tested
implementation; this was not a fresh evaluation of the 0.3.1 or 0.3.2 wheel.

The older README reported results from a different setup and different
samples. DSA's clean-case false-positive rate changed from 15% to 0%, and the
combined CRA/DMA/NIS2 sample from 5% to 0%, but GDPR worsened from 6% to 8%
and EU AI Act recall fell from 93% to 64%. This historical comparison cannot
attribute those differences solely to the model change. Fifty cases per
dataset, only 25 of them clean, do not establish production error rates or
guarantee zero false alarms. Training overlap was not audited in this run.

## Evaluating changes

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
