import json

import pytest
from compare_regulation_evaluations import compare, read_cases


def case(expected, actual, *, error=None):
    return {"id": "example", "type": "case", "expected_articles": expected,
            "actual_articles": actual, "candidates": [{"description": "Candidate"}],
            "error": error, "correct": True}


def test_comparison_recomputes_scores_and_distinguishes_error_from_clean_control():
    before = {"example": case([], [])}
    after = {"example": case([], [], error="validator timed out")}
    report = compare(before, after)
    assert report["regressed_cases"] == ["example"]
    assert report["after"]["exact_article_matches"] == 0
    assert report["after"]["errors"] == 1


def test_comparison_rejects_moved_goalposts_and_missing_cases():
    before = {"example": case(["eu_ai_act_art53"], [])}
    with pytest.raises(ValueError, match="expected labels changed"):
        compare(before, {"example": case([], [])})
    with pytest.raises(ValueError, match="same case IDs"):
        compare(before, {})


def test_incomplete_runs_and_duplicate_ids_cannot_inflate_a_score(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_text(json.dumps(case([], [])) + "\n")
    with pytest.raises(ValueError, match="incomplete"):
        read_cases([path])
    with path.open("a") as stream:
        stream.write(json.dumps({"type": "summary", "total": 1}) + "\n")
    with pytest.raises(ValueError, match="duplicate"):
        read_cases([path, path])
