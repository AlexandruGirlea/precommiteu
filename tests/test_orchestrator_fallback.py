from __future__ import annotations

import pathlib

import pytest

from precommiteu import scan as scan_mod
from precommiteu.agents.orchestrator import OrchestratorRun

REG_DOCS = pathlib.Path(scan_mod.__file__).parent / "regulations"

UNANALYSED = ["emit", "budget_exhausted_iters"]
ANALYSED = ["file_ignored", "unknown_regulation", "file_unreadable"]


def _run(reason: str, *, detector_called: bool) -> OrchestratorRun:
    run = OrchestratorRun(exit_reason=reason)
    run.detector_called = detector_called
    return run


@pytest.fixture
def harness(tmp_path, monkeypatch):
    target = tmp_path / "app.py"
    target.write_text("import logging\n\n\ndef f():\n    pass\n", encoding="utf-8")
    calls: list[str] = []

    def scan_file(orch_run: OrchestratorRun) -> tuple[list, list[str], dict]:
        calls.clear()
        events: list[dict] = []

        def fake_orchestrator(**_kwargs):
            calls.append("orchestrator")
            return orch_run

        def fake_direct(**kwargs):
            calls.append("direct")
            events.append({"direct_wall_seconds": kwargs["wall_seconds"]})
            return _run("direct", detector_called=True)

        monkeypatch.setattr(scan_mod, "run_orchestrator", fake_orchestrator)
        monkeypatch.setattr(scan_mod, "run_direct", fake_direct)

        progress: list[dict] = []
        findings, _analysed = scan_mod._scan_one_file(
            file_path=target,
            regulation="gdpr",
            repo_root=tmp_path,
            regulation_docs_dir=REG_DOCS,
            loop_model=object(),
            detector_model=object(),
            validator_model=object(),
            max_iterations=12,
            wall_seconds_per_file=90.0,
            counters=scan_mod._RegCounters(),
            on_progress=progress.append,
            on_finding=None,
            advisories=[],
            agent_mode="orchestrator",
        )
        done = next(e for e in progress if e["event"] == "orchestrator_done")
        done["_direct_budget"] = events[0]["direct_wall_seconds"] if events else None
        return findings, list(calls), done

    return scan_file


@pytest.mark.parametrize("reason", UNANALYSED)
def test_falls_back_when_detector_never_ran(harness, reason):
    _findings, calls, done = harness(_run(reason, detector_called=False))

    assert calls == ["orchestrator", "direct"]
    assert done["fell_back"] is True
    assert done["route"] == "orchestrator"
    assert done["detector_called"] is True
    assert done["exit_reason"] == "direct"


@pytest.mark.parametrize("reason", UNANALYSED)
def test_no_fallback_when_detector_already_ran(harness, reason):
    _findings, calls, done = harness(_run(reason, detector_called=True))

    assert calls == ["orchestrator"]
    assert done["fell_back"] is False
    assert done["exit_reason"] == reason


@pytest.mark.parametrize("reason", ANALYSED)
def test_no_fallback_when_there_was_nothing_to_analyse(harness, reason):
    _findings, calls, done = harness(_run(reason, detector_called=False))

    assert calls == ["orchestrator"]
    assert done["fell_back"] is False
    assert done["exit_reason"] == reason


def test_loop_step_failed_still_reports_a_failed_file(harness):
    # It already drives exit 3; falling back would mask a broken agent.
    _findings, calls, done = harness(_run("loop_step_failed", detector_called=False))

    assert calls == ["orchestrator"]
    assert done["fell_back"] is False
    assert done["exit_reason"] == "loop_step_failed"
    assert "loop_step_failed" in scan_mod._ANALYSIS_FAILURE_REASONS


def test_fallback_stays_inside_the_per_file_budget(harness):
    _findings, _calls, done = harness(_run("emit", detector_called=False))

    assert 0.0 <= done["_direct_budget"] <= 90.0


def test_unanalysed_reasons_are_disjoint_from_failure_reasons():
    assert not (scan_mod._UNANALYSED_REASONS & scan_mod._ANALYSIS_FAILURE_REASONS)


def test_wall_clock_exhaustion_does_not_trigger_a_pointless_fallback(harness):
    # budget_exhausted_time means the budget is spent by definition, so a
    # fallback would get max(0.0, ...) == 0 seconds and analyse nothing.
    assert "budget_exhausted_time" not in scan_mod._UNANALYSED_REASONS

    _findings, calls, done = harness(
        _run("budget_exhausted_time", detector_called=False)
    )

    assert calls == ["orchestrator"]
    assert done["fell_back"] is False
    assert done["exit_reason"] == "budget_exhausted_time"
