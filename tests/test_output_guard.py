from __future__ import annotations

import pytest

from precommiteu.cli import DEFAULT_LOG_FILE, main

OUTPUT_FLAGS = ["--json-out", "--report", "--sarif", "--out", "--log-file"]


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    # No models configured: a run that clears the guard fails later with
    # the model error, which is how these tests tell the two apart.
    monkeypatch.delenv("PRECOMMITEU_MODELS_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("import logging\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("flag", OUTPUT_FLAGS)
def test_existing_output_target_refuses_to_run(workdir, capsys, flag):
    target = workdir / "existing.out"
    target.write_text("user data", encoding="utf-8")

    assert main(["scan", "app.py", flag, str(target)]) == 2

    err = capsys.readouterr().err
    assert f"{flag} target already exists" in err
    assert "never overwrites your files" in err
    assert target.read_text(encoding="utf-8") == "user data"


def test_guard_runs_before_any_model_resolution(workdir, capsys):
    target = workdir / "existing.json"
    target.write_text("{}", encoding="utf-8")

    assert main(["scan", "app.py", "--json-out", str(target)]) == 2

    err = capsys.readouterr().err
    assert "already exists" in err
    assert "no model paths configured" not in err


def test_force_bypasses_the_guard(workdir, capsys):
    target = workdir / "existing.json"
    target.write_text("{}", encoding="utf-8")

    assert main(["scan", "app.py", "--json-out", str(target), "--force"]) == 2

    err = capsys.readouterr().err
    assert "already exists" not in err
    assert "no model paths configured" in err


def test_default_log_file_does_not_block_repeat_scans(workdir, capsys):
    (workdir / DEFAULT_LOG_FILE).write_text("previous run\n", encoding="utf-8")

    assert main(["scan", "app.py"]) == 2

    err = capsys.readouterr().err
    assert "already exists" not in err
    assert "no model paths configured" in err


def test_explicitly_passed_log_file_is_guarded(workdir, capsys):
    target = workdir / "my.log"
    target.write_text("mine", encoding="utf-8")

    assert main(["scan", "app.py", "--log-file", str(target)]) == 2

    assert "--log-file target already exists" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "mine"


def test_missing_targets_pass_the_guard(workdir, capsys):
    assert main(["scan", "app.py", "--json-out", "fresh.json"]) == 2

    err = capsys.readouterr().err
    assert "already exists" not in err
    assert "no model paths configured" in err
    assert not (workdir / "fresh.json").exists()


def test_dry_run_ignores_existing_outputs(workdir, capsys):
    target = workdir / "existing.json"
    target.write_text("user data", encoding="utf-8")

    assert main(["scan", "app.py", "--dry-run", "--json-out", str(target)]) == 0

    assert target.read_text(encoding="utf-8") == "user data"


def test_first_clashing_target_is_reported(workdir, capsys):
    (workdir / "a.json").write_text("a", encoding="utf-8")
    (workdir / "b.sarif").write_text("b", encoding="utf-8")

    assert (
        main(
            [
                "scan",
                "app.py",
                "--json-out",
                str(workdir / "a.json"),
                "--sarif",
                str(workdir / "b.sarif"),
            ]
        )
        == 2
    )

    err = capsys.readouterr().err
    assert "--json-out target already exists" in err
    assert (workdir / "a.json").read_text(encoding="utf-8") == "a"
    assert (workdir / "b.sarif").read_text(encoding="utf-8") == "b"
