"""Compare saved model runs with matching cases and expected article labels.

Accepts multiple JSONL files on each side. Exits nonzero for a regression or an
after-run error. This format can be reused when evaluating another regulation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_cases(paths: list[Path]) -> dict[str, dict]:
    cases = {}
    for path in paths:
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        rows = [row for row in records if row.get("type") == "case"]
        summaries = [row for row in records if row.get("type") == "summary"]
        if len(summaries) != 1 or summaries[0]["total"] != len(rows):
            raise ValueError(f"incomplete or ambiguous evaluation: {path}")
        for row in rows:
            if row["id"] in cases:
                raise ValueError(f"duplicate case ID: {row['id']}")
            cases[row["id"]] = row
    if not cases:
        raise ValueError("no evaluated cases")
    return cases


def exact(row: dict) -> bool:
    # Recompute from raw output; do not trust the evaluator's cached score.
    return not row.get("error") and set(row["expected_articles"]) == set(row["actual_articles"])


def metrics(cases: dict[str, dict]) -> dict[str, int]:
    rows = list(cases.values())
    positives = [row for row in rows if row["expected_articles"]]
    controls = [row for row in rows if not row["expected_articles"]]
    misses = [row for row in positives if not row["actual_articles"] and not row.get("error")]
    return {
        "cases": len(rows), "exact_article_matches": sum(exact(row) for row in rows),
        "positive_cases": len(positives), "control_cases": len(controls),
        "positive_exact_article_matches": sum(exact(row) for row in positives),
        "missed_positive_cases": len(misses),
        "detector_misses": sum(not row["candidates"] for row in misses),
        "validator_misses": sum(bool(row["candidates"]) for row in misses),
        "wrong_article_positive_cases": sum(
            bool(row["actual_articles"]) and not exact(row) and not row.get("error")
            for row in positives
        ),
        "false_positive_cases": sum(bool(row["actual_articles"]) for row in controls),
        "errors": sum(bool(row.get("error")) for row in rows),
    }


def compare(before: dict[str, dict], after: dict[str, dict]) -> dict:
    if before.keys() != after.keys():
        raise ValueError("before and after must contain exactly the same case IDs")
    for case_id in before:
        if set(before[case_id]["expected_articles"]) != set(after[case_id]["expected_articles"]):
            raise ValueError(f"expected labels changed: {case_id}")
    return {
        "before": metrics(before), "after": metrics(after),
        "improved_cases": [key for key in before if not exact(before[key]) and exact(after[key])],
        "regressed_cases": [key for key in before if exact(before[key]) and not exact(after[key])],
        "remaining_failures": [
            {"id": row["id"], "expected": row["expected_articles"],
             "actual": row["actual_articles"], "error": row.get("error")}
            for row in after.values() if not exact(row)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, action="append", required=True)
    parser.add_argument("--after", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare(read_cases(args.before), read_cases(args.after))
    report = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(report)
    print(report, end="")
    return int(bool(result["regressed_cases"]) or bool(result["after"]["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
