from __future__ import annotations

import shutil
import subprocess

from precommiteu import __version__
from precommiteu.llama_server import BUILD_RE, MIN_BUILD
from precommiteu.ui import install, runner, settings


def _row(label: str, ok: bool, det: str, args: dict | None = None,
         fix: dict | None = None) -> dict:
    return {"label": label, "ok": ok, "det": det, "args": args or {}, "fix": fix}


def _cmd(command: str) -> dict:
    return {"auto": False, "command": command}


def _llama() -> dict:
    binary = shutil.which("llama-server")
    if binary is None:
        return _row("Local inference engine", False, "engine.missing",
                    fix=_cmd(install.engine_command()))
    try:
        out = subprocess.run([binary, "--version"], capture_output=True,
                             text=True, check=False, timeout=5)
    except subprocess.TimeoutExpired:
        return _row("Local inference engine", True, "engine.unknown", {"path": binary})
    match = BUILD_RE.search((out.stdout or "") + "\n" + (out.stderr or ""))
    # llama.cpp has changed this string before. An unreadable version is not a
    # reason to block a machine that has a working binary.
    if match is None:
        return _row("Local inference engine", True, "engine.unknown", {"path": binary})
    build = int(match.group(1))
    if build < MIN_BUILD:
        return _row("Local inference engine", False, "engine.old",
                    {"build": build, "min": MIN_BUILD},
                    _cmd(install.engine_upgrade()))
    return _row("Local inference engine", True, "engine.ok",
                {"build": build, "path": binary})


def _scanner() -> dict:
    return _row("Scanner", True, "scanner.ok",
                {"version": f"precommiteu {__version__}"})


# Only the shared base belongs here. Which adapter you want is a choice made
# two steps later, on the regulation screen, and it is downloaded there.
def _base() -> dict:
    base = settings.models_dir() / install.BASE
    fix = {"action": "base", "auto": True, "command": None}
    if not base.exists():
        return _row("Base model", False, "models.nobase", fix=fix)
    size = base.stat().st_size
    if size != install.BASE_BYTES:
        return _row("Base model", False, "models.truncated",
                    {"size": f"{size:,}", "expected": f"{install.BASE_BYTES:,}"}, fix)
    return _row("Base model", True, "models.ok",
                {"gib": f"{install.BASE_BYTES / 1024 ** 3:.2f}"})


def _git() -> dict:
    binary = shutil.which("git")
    row = _row("Git", bool(binary), "git.ok" if binary else "git.missing",
               {"path": binary or ""})
    row["optional"] = True
    return row


def _orphans(scanning: bool) -> dict:
    pids = runner.server_pids()
    if not pids:
        return _row("No stale processes", True, "proc.none")
    if scanning:
        return _row("No stale processes", True, "proc.inuse", {"n": len(pids)})
    return _row("No stale processes", False, "proc.stale", {"n": len(pids)},
                {"action": "kill", "auto": True, "command": None})


def run(scanning: bool) -> list[dict]:
    return [_llama(), _scanner(), _base(), _git(), _orphans(scanning)]
