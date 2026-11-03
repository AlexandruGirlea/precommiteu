from __future__ import annotations

import os
import pathlib
import shlex
import subprocess
import sys
import textwrap

import pytest

from precommiteu import scan as scan_mod
from precommiteu.cli import main

PROJECT = pathlib.Path(__file__).resolve().parents[1]


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()


def commit(repo, files):
    for name, content in files.items():
        path = repo / name
        if content is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "fixture")
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.delenv("GIT_DIFF_BASE", raising=False)
    monkeypatch.setenv("GIT_MERGE_TARGET_BRANCH", "main")
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-qb", "main")
    git(path, "config", "user.name", "Alexandru Girlea")
    git(path, "config", "user.email", "alex@girlea.ro")
    git(path, "remote", "add", "origin", str(path))
    commit(path, {
        "src/app.py": "original = 1\n",
        "shared/helper.py": "helper = 1\n",
        ".eu-ignore": "ignored.py\n",
    })
    return path


def run_action(repo, tmp_path, *, event="push", before=""):
    blocks = (PROJECT / "action.yml").read_text().split("      run: |\n")
    prepare = textwrap.dedent(blocks[1].split("\n    - name:", 1)[0])
    scan = textwrap.dedent(blocks[2])
    output = tmp_path / "github-output"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    executable = bin_dir / "precommiteu"
    executable.write_text(
        f"#!/bin/sh\nexec {shlex.quote(sys.executable)} "
        '-m precommiteu "$@" --dry-run\n'
    )
    executable.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PYTHONPATH": str(PROJECT / "src"),
        "TARGET": "main", "EVENT_NAME": event, "BEFORE": before,
        "GITHUB_OUTPUT": str(output), "GIT_MERGE_TARGET_BRANCH": "origin/main",
        "REGULATIONS": "gdpr", "PATHS": "", "SARIF": "scan.sarif",
        "SUMMARY": "summary.md", "FAIL_ON_FINDINGS": "true",
    }
    shell = ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c"]
    prepared = subprocess.run(
        [*shell, prepare], cwd=repo, env=env, capture_output=True, text=True,
        check=False,
    )
    if prepared.returncode:
        return prepared
    values = (
        dict(line.split("=", 1) for line in output.read_text().splitlines())
        if output.exists() else {}
    )
    env["GIT_DIFF_BASE"] = values.get("base", "")
    return subprocess.run(
        [*shell, scan], cwd=repo, env=env, capture_output=True, text=True,
        check=False,
    )


def test_subdirectory_uses_root_filtering_and_full_repo(repo, monkeypatch, capsys):
    git(repo, "checkout", "-qb", "feature")
    commit(repo, {
        "src/app.py": "original = 1\nnew = 2\n",
        "shared/helper.py": "helper = 2\n",
        "src/ignored.py": "ignored = 1\n",
        "src/nouveau café.py": "x = 1\n",
        "notes.txt": "notes\n", "README.md": "docs\n",
        "tests/test_app.py": "x = 1\n",
    })
    monkeypatch.chdir(repo / "src")
    assert main(["scan", "--ci", "--dry-run"]) == 0
    assert set(capsys.readouterr().out.splitlines()) == {
        "src/app.py", "shared/helper.py", "src/nouveau café.py",
    }
    seen = {}
    monkeypatch.setattr(scan_mod, "scan_paths", lambda paths, **kw: seen.update(kw))
    scan_mod.scan_diff()
    assert seen["repo_root"] == repo.resolve()


@pytest.mark.parametrize("shallow", [False, True])
def test_action_push_includes_every_commit(repo, tmp_path, shallow):
    before = git(repo, "rev-parse", "HEAD")
    commit(repo, {"src/app.py": "original = 2\n"})
    commit(repo, {"shared/helper.py": "helper = 2\n", "README.md": "docs\n"})
    checkout = repo
    if shallow:
        checkout = tmp_path / "shallow"
        git(tmp_path, "clone", "--quiet", "--depth", "1", repo.as_uri(), str(checkout))
    result = run_action(checkout, tmp_path, before=before)
    assert result.returncode == 0, result.stderr
    assert set(result.stdout.splitlines()) == {"src/app.py", "shared/helper.py"}


def test_action_force_push_compares_previous_tree(repo, tmp_path):
    base = git(repo, "rev-parse", "HEAD")
    before = commit(repo, {"src/app.py": "original = 2\n"})
    git(repo, "checkout", "-qb", "replacement", base)
    commit(repo, {"shared/helper.py": "helper = 2\n"})
    result = run_action(repo, tmp_path, before=before)
    assert result.returncode == 0, result.stderr
    assert set(result.stdout.splitlines()) == {"src/app.py", "shared/helper.py"}


def test_action_new_branch_scans_all_code_without_main(repo, tmp_path):
    git(repo, "branch", "-m", "new-branch")
    result = run_action(repo, tmp_path, before="0" * 40)
    assert result.returncode == 0, result.stderr
    assert set(result.stdout.splitlines()) == {"src/app.py", "shared/helper.py"}


@pytest.mark.parametrize("before", ["", "f" * 40])
def test_action_missing_push_baseline_fails(repo, tmp_path, before):
    result = run_action(repo, tmp_path, before=before)
    assert result.returncode != 0


@pytest.mark.parametrize("shallow", [False, True])
def test_action_pr_uses_remote_target_and_merge_base(repo, tmp_path, shallow):
    git(repo, "checkout", "-qb", "feature")
    commit(repo, {"src/app.py": "original = 2\n"})
    git(repo, "checkout", "main")
    commit(repo, {"target_only.py": "target_only = True\n"})
    git(repo, "checkout", "feature")
    checkout = tmp_path / "checkout"
    options = ["--depth", "1"] if shallow else []
    git(tmp_path, "clone", "--quiet", *options, repo.as_uri(), str(checkout))
    git(checkout, "branch", "main", "HEAD")
    result = run_action(checkout, tmp_path, event="pull_request")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["src/app.py"]


def test_push_api_uses_base_without_resolving_main(repo, monkeypatch):
    before = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "-m", "trunk")
    commit(repo, {"src/app.py": "original = 2\n"})
    monkeypatch.setenv("GIT_DIFF_BASE", before)
    seen = []
    monkeypatch.setattr(scan_mod, "scan_paths", lambda paths, **kw: seen.extend(paths))
    scan_mod.scan_diff(repo_root=repo)
    assert seen == [(repo / "src/app.py").resolve()]
