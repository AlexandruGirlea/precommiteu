from __future__ import annotations

import contextlib
import json
import os
import pathlib

import pytest

from precommiteu import scan as scan_mod
from precommiteu.agents.orchestrator import OrchestratorRun
from precommiteu.scan_ledger import ScanLedger, default_ledger_path

CODE = "def save(user):\n    db.write(user.email)\n    return True\n"
EVIDENCE = "db.write(user.email)"


class Harness:
    def __init__(self, repo: pathlib.Path, model: pathlib.Path) -> None:
        self.repo = repo
        self.model = model
        self.analysed: list[str] = []
        self.servers = 0
        self.exit_reason = "direct"
        self.interrupt_on: str | None = None
        self.candidates: list[dict] | None = None

    def run(self, **kwargs):
        self.analysed.clear()
        events: list[dict] = []
        result = scan_mod.scan_paths(
            [self.repo],
            regulations=kwargs.pop("regulations", ("gdpr",)),
            orchestrator_model_path=self.model,
            repo_root=self.repo,
            on_progress=events.append,
            **kwargs,
        )
        return result, events


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "one.py").write_text(CODE, encoding="utf-8")
    (repo / "two.py").write_text(CODE, encoding="utf-8")
    harness = Harness(repo, tmp_path / "base.gguf")

    @contextlib.contextmanager
    def fake_server(*_args, **_kwargs):
        harness.servers += 1
        yield object()

    def fake_direct(*, chunks, file_label, **_kwargs):
        if harness.interrupt_on == file_label:
            raise KeyboardInterrupt
        harness.analysed.append(file_label)
        run = OrchestratorRun(exit_reason=harness.exit_reason)
        run.detector_called = True
        run.validator_called = True
        for chunk in chunks:
            run.consult_log.record(chunk.id, chunk.text)
        if harness.candidates is not None:
            run.candidates_store.put(file_label, harness.candidates)
            return run
        run.kept_findings.append(
            {
                "article_no": "Article 32",
                "code_evidence": EVIDENCE,
                "description": f"personal data written unprotected in {file_label}",
                "chunk_id": chunks[0].id,
            }
        )
        return run

    monkeypatch.setattr(scan_mod, "launch_llama_server", fake_server)
    monkeypatch.setattr(scan_mod, "build_chat_model", lambda *a, **k: object())
    monkeypatch.setattr(scan_mod, "run_direct", fake_direct)
    monkeypatch.setattr(scan_mod, "_load_case_index", lambda _r: None)
    return harness


def _ledger_doc(repo: pathlib.Path, regulation: str = "gdpr") -> dict:
    return json.loads(
        default_ledger_path(repo, regulation).read_text(encoding="utf-8")
    )


def test_first_scan_records_every_analysed_file(harness):
    result, _events = harness.run()

    assert harness.analysed == ["one.py", "two.py"]
    assert len(result.findings) == 2
    doc = _ledger_doc(harness.repo)
    assert doc["version"] == 1
    assert doc["regulation"] == "gdpr"
    assert doc["target"] == str(harness.repo)
    assert sorted(doc["files"]) == ["one.py", "two.py"]
    assert doc["files"]["one.py"]["sha256"]


def test_unchanged_files_are_reused_with_their_findings(harness):
    first, _ = harness.run()
    second, events = harness.run()

    assert harness.analysed == []
    assert harness.servers == 1, "a fully cached scan must not load a model"
    assert [f.model_dump() for f in second.findings] == [
        f.model_dump() for f in first.findings
    ]
    reused = [e for e in events if e["event"] == "file_reused"]
    assert [e["file"] for e in reused] == ["one.py", "two.py"]
    assert all(e["event"] != "file_start" for e in events)
    status = second.statuses[0]
    assert status.status == "scanned"
    assert "2 of 2 file(s) reused" in status.detail


def test_only_changed_files_are_rescanned_and_the_report_stays_complete(harness):
    harness.run()
    (harness.repo / "two.py").write_text(CODE + "print(1)\n", encoding="utf-8")

    result, events = harness.run()

    assert harness.analysed == ["two.py"]
    assert sorted(f.file for f in result.findings) == ["one.py", "two.py"]
    assert [e["file"] for e in events if e["event"] == "file_reused"] == ["one.py"]


def test_a_touched_file_is_not_rescanned_and_the_stamp_is_refreshed(harness):
    harness.run()
    before = _ledger_doc(harness.repo)["files"]["one.py"]["mtime_ns"]
    (harness.repo / "one.py").touch()

    _result, _events = harness.run()

    assert harness.analysed == []
    assert _ledger_doc(harness.repo)["files"]["one.py"]["mtime_ns"] != before


def test_the_fast_path_trusts_size_plus_mtime(harness):
    # Rehashing every byte of every file is the cost this feature removes, so
    # an edit that keeps both the size and the mtime is deliberately missed.
    harness.run()
    path = harness.repo / "two.py"
    before = path.stat()
    path.write_text(CODE.replace("save", "SAVE"), encoding="utf-8")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))

    harness.run()

    assert harness.analysed == []
    assert path.stat().st_size == before.st_size


@pytest.mark.parametrize(
    "reason", ["budget_exhausted_time", "budget_exhausted_iters", "direct_partial"]
)
def test_a_file_that_was_not_cleanly_analysed_is_rescanned(harness, reason):
    harness.exit_reason = reason
    harness.run()

    assert _ledger_doc(harness.repo)["files"] == {}

    harness.run()

    assert harness.analysed == ["one.py", "two.py"]


def test_an_interrupt_keeps_the_files_already_done(harness):
    harness.interrupt_on = "two.py"
    harness.run()

    assert list(_ledger_doc(harness.repo)["files"]) == ["one.py"]

    harness.interrupt_on = None
    harness.run()

    assert harness.analysed == ["two.py"]


def test_a_deleted_file_leaves_the_ledger_and_the_results(harness):
    harness.run()
    (harness.repo / "two.py").unlink()

    result, _events = harness.run()

    assert [f.file for f in result.findings] == ["one.py"]
    assert list(_ledger_doc(harness.repo)["files"]) == ["one.py"]


def test_rescan_all_scans_everything_and_rewrites_the_entries(harness):
    harness.run()
    before = _ledger_doc(harness.repo)["files"]["one.py"]["scanned_at"]

    _result, events = harness.run(rescan_all=True)

    assert harness.analysed == ["one.py", "two.py"]
    assert all(e["event"] != "file_reused" for e in events)
    assert _ledger_doc(harness.repo)["files"]["one.py"]["scanned_at"] >= before


@pytest.mark.parametrize(
    "corrupt",
    [
        "{ not json",
        json.dumps({"version": 99, "files": {}}),
        json.dumps({"version": 1, "regulation": "dora", "target": "", "files": {}}),
    ],
)
def test_an_unusable_ledger_means_a_full_scan(harness, corrupt):
    harness.run()
    default_ledger_path(harness.repo, "gdpr").write_text(corrupt, encoding="utf-8")

    harness.run()

    assert harness.analysed == ["one.py", "two.py"]


def test_a_ledger_from_another_target_is_not_reused(harness, tmp_path):
    harness.run()
    other = ScanLedger.load(tmp_path / "elsewhere", "gdpr")
    other.path = default_ledger_path(harness.repo, "gdpr")
    other.entries = _ledger_doc(harness.repo)["files"]
    other.save()

    harness.run()

    assert harness.analysed == ["one.py", "two.py"]


def test_scan_log_overrides_the_location(harness, tmp_path):
    ledger = tmp_path / "nested" / "gdpr.json"

    harness.run(scan_log=ledger)

    assert not default_ledger_path(harness.repo, "gdpr").exists()
    assert json.loads(ledger.read_text(encoding="utf-8"))["files"]

    harness.run(scan_log=ledger)

    assert harness.analysed == []


def test_one_scan_log_cannot_serve_several_regulations(harness, tmp_path):
    with pytest.raises(ValueError, match="one regulation"):
        harness.run(scan_log=tmp_path / "l.json", regulations=("gdpr", "dora"))


def test_incremental_off_neither_reads_nor_writes_a_ledger(harness):
    harness.run()
    stamp = default_ledger_path(harness.repo, "gdpr").stat().st_mtime_ns

    _result, events = harness.run(incremental=False)

    assert harness.analysed == ["one.py", "two.py"]
    assert all(e["event"] != "file_reused" for e in events)
    assert default_ledger_path(harness.repo, "gdpr").stat().st_mtime_ns == stamp


def test_advisories_come_back_with_a_reused_file(harness):
    harness.candidates = [{"description": "consent never checked"}]

    first, _ = harness.run()
    second, _ = harness.run()

    assert harness.analysed == []
    assert [a.model_dump() for a in second.advisories] == [
        a.model_dump() for a in first.advisories
    ]


def test_ci_does_not_touch_the_ledger(monkeypatch, tmp_path):
    seen: dict = {}
    monkeypatch.setattr(scan_mod, "_require_git_repo", lambda _cwd: None)
    monkeypatch.setattr(scan_mod, "_resolve_merge_target", lambda t, _cwd: t)
    monkeypatch.setattr(scan_mod, "_changed_files", lambda _ref, _cwd: [tmp_path / "a.py"])
    monkeypatch.setattr(scan_mod, "scan_paths", lambda *a, **k: seen.update(k))

    scan_mod.scan_diff(merge_target="main", repo_root=tmp_path)

    assert seen["incremental"] is False
