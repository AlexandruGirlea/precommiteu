from __future__ import annotations

import json

from conftest import make_finding

from precommiteu.reporting import IncrementalReporter
from precommiteu.src.reporters import write_json_report, write_sarif_report
from precommiteu.src.sarif import SARIF_VERSION, TOOL_NAME
from precommiteu.src.scanner import dedup_findings
from precommiteu.src.schemas import ScanResult


def _result(*findings) -> ScanResult:
    return ScanResult(findings=list(findings), statuses=[])


def test_json_report_round_trips_finding_fields(tmp_path):
    finding = make_finding()
    path = tmp_path / "out.json"

    write_json_report(_result(finding), path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["findings"][0]["regulation"] == "gdpr"
    assert payload["findings"][0]["probable_article_id"] == "gdpr_art32"
    assert payload["findings"][0]["start_line"] == 10
    assert payload["advisories"] == []


def test_sarif_report_has_required_top_level_shape(tmp_path):
    path = tmp_path / "out.sarif"

    write_sarif_report(_result(make_finding()), path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["version"] == SARIF_VERSION
    assert payload["$schema"]
    run = payload["runs"][0]
    assert run["tool"]["driver"]["name"] == TOOL_NAME
    assert len(run["results"]) == 1
    result = run["results"][0]
    assert result["ruleId"] == "gdpr_art32"
    location = result["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "user_store.py"
    assert location["region"]["startLine"] == 10


def test_sarif_omits_findings_without_a_citable_article(tmp_path):
    path = tmp_path / "out.sarif"

    write_sarif_report(_result(make_finding(probable_article_id=None)), path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["runs"][0]["results"] == []


def test_dedup_drops_identical_findings_but_keeps_distinct_ones():
    a = make_finding()
    same = make_finding(description=a.description.upper())
    other = make_finding(start_line=99, end_line=100)

    assert len(dedup_findings([a, same, other])) == 2


def test_incremental_reporter_snapshots_before_finalize(tmp_path):
    json_out = tmp_path / "live.json"
    reporter = IncrementalReporter(json_out=json_out)

    reporter.add_finding(make_finding())
    reporter.snapshot()
    mid_run = json.loads(json_out.read_text(encoding="utf-8"))

    assert len(mid_run["findings"]) == 1

    reporter.finalize(_result(make_finding(), make_finding(start_line=99)))

    assert len(json.loads(json_out.read_text(encoding="utf-8"))["findings"]) == 2
