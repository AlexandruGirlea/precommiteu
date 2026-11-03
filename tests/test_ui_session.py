from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from precommiteu.ui import runner, settings


@pytest.mark.parametrize(
    ("exit_code", "phase"), [(0, "done"), (130, "paused"), (3, "failed")],
)
def test_terminal_status_and_elapsed_time_survive_session_reload(
    tmp_path, monkeypatch, exit_code, phase,
):
    monkeypatch.setattr(settings, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(settings, "FILE", tmp_path / "settings.json")
    monkeypatch.setattr(settings, "SCANS_DIR", tmp_path / "scans")
    clock = [100.0]
    monkeypatch.setattr(runner.time, "monotonic", lambda: clock[0])

    def scanner(argv, **_kwargs):
        report = Path(argv[argv.index("--report") + 1])
        events = [{"event": "file_start", "payload": {
            "file": "sample.py", "chunks": 1,
        }}]
        if exit_code == 0:
            events.extend([
                {"event": "orchestrator_done", "payload": {
                    "route": "direct", "exit_reason": "direct",
                }},
                {"event": "file_done", "payload": {"kept": 0}},
            ])
        elif exit_code == 130:
            events.append({"event": "scan_interrupted"})
        else:
            events.append({"event": "file_error", "payload": {
                "file": "sample.py", "error": "scan failed",
            }})
        report.write_text("".join(json.dumps(event) + "\n" for event in events))
        clock[0] = 160.0
        return SimpleNamespace(
            returncode=exit_code, stderr=io.StringIO(), poll=lambda: exit_code,
        )

    monkeypatch.setattr(runner.subprocess, "Popen", scanner)
    session = runner.Session(tmp_path, "gdpr")
    session.files = ["sample.py"]
    session.plan = list(session.files)
    session.forecast = {"sample.py": {"route": "direct", "chunks": 1}}
    monkeypatch.setattr(session, "refresh_plan", lambda: None)
    session.start()
    session.thread.join(timeout=5)
    assert not session.thread.is_alive()
    finished = session.snapshot()
    assert finished["phase"] == phase
    assert finished["elapsed_s"] == 60
    assert bool(finished["error"]) == (exit_code == 3)

    clock[0] = 400.0
    assert session.snapshot()["elapsed_s"] == 60
    restored = runner.Session(tmp_path, "gdpr").snapshot()
    assert restored["phase"] == phase
    assert restored["error"] == finished["error"]
    assert restored["elapsed_s"] == 60
    assert runner.Session(tmp_path / "different", "gdpr").phase == "idle"
