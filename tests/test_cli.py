from __future__ import annotations

import shutil

import pytest

from precommiteu.cli import _parse_regulations, main


def test_ci_mode_rejects_positional_paths(capsys):
    assert main(["scan", "--ci", "src/"]) == 2
    assert "--ci derives paths from `git diff`" in capsys.readouterr().err


def test_scan_requires_paths_or_ci(capsys):
    assert main(["scan"]) == 2
    assert "requires either positional paths or --ci" in capsys.readouterr().err


def test_unknown_regulation_exits_two(capsys):
    with pytest.raises(SystemExit) as exc:
        _parse_regulations("gdpr,hipaa")

    assert exc.value.code == 2
    assert "not packaged" in capsys.readouterr().err


def test_regulations_are_parsed_in_order_and_stripped():
    assert _parse_regulations(" gdpr , dora ") == ("gdpr", "dora")


def test_empty_regulations_falls_back_to_default():
    assert _parse_regulations("") == ("gdpr",)


def test_dry_run_lists_files_without_loading_a_model(risky_code, tmp_path, capsys):
    # Copied out of tests/ because the scanner skips test paths by design.
    app = tmp_path / "app"
    shutil.copytree(risky_code, app)

    assert main(["scan", "--dry-run", str(app)]) == 0

    listed = capsys.readouterr().out.splitlines()
    assert {line.rsplit("/", 1)[-1] for line in listed if line} == {
        "CrmSyncJob.java",
        "SupportAuditTrail.java",
        "campaign_mailer.py",
        "models.py",
        "user_store.py",
    }


@pytest.mark.parametrize("flag", [["--rescan-all"], ["--scan-log", "l.json"]])
def test_ci_rejects_the_ledger_flags(capsys, flag):
    assert main(["scan", "--ci", *flag]) == 2
    assert "--ci keeps no scan ledger" in capsys.readouterr().err


def test_one_scan_log_cannot_serve_several_regulations(capsys, tmp_path):
    argv = ["scan", str(tmp_path), "--scan-log", "l.json", "--regulations", "gdpr,dora"]

    assert main(argv) == 2
    assert "a single --scan-log" in capsys.readouterr().err


def test_this_command_succeeds():
    assert main(["this"]) == 0
