from __future__ import annotations

from precommiteu.src.file_filter import collect_code_files, is_code_file

EXPECTED = {
    "CrmSyncJob.java",
    "SupportAuditTrail.java",
    "campaign_mailer.py",
    "models.py",
    "user_store.py",
}


def test_collects_every_risky_code_file(risky_code):
    selected, oversized = collect_code_files([risky_code], risky_code)

    assert {p.name for p in selected} == EXPECTED
    assert oversized == []


def test_non_code_files_are_not_collected(risky_code, tmp_path):
    (tmp_path / "notes.txt").write_text("not code", encoding="utf-8")
    (tmp_path / "keep.py").write_text("x = 1\n", encoding="utf-8")

    selected, _ = collect_code_files([tmp_path], tmp_path)

    assert {p.name for p in selected} == {"keep.py"}
    assert not is_code_file(tmp_path / "notes.txt", tmp_path)


def test_oversized_files_are_reported_separately(risky_code):
    selected, oversized = collect_code_files([risky_code], risky_code, max_bytes=100)

    assert selected == []
    assert {p.name for p in oversized} == EXPECTED


def test_repeated_paths_are_deduplicated(risky_code):
    target = risky_code / "user_store.py"
    selected, _ = collect_code_files([target, target, risky_code], risky_code)

    assert len(selected) == len(EXPECTED)
