from __future__ import annotations

import os
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


MIN_MEMORY_GIB = 32


def _shared(name: str, label: str) -> dict:
    path = settings.models_dir() / name
    expected = install.SHARED[name]
    fix = {"action": "base", "auto": True, "command": None}
    if not path.exists():
        return _row(label, False, "models.nobase", fix=fix)
    size = path.stat().st_size
    if size != expected:
        return _row(label, False, "models.truncated",
                    {"size": f"{size:,}", "expected": f"{expected:,}"}, fix)
    return _row(label, True, "models.ok", {"gib": f"{expected / 1024 ** 3:.2f}"})


def _memory() -> dict:
    try:
        gib = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
    except (AttributeError, ValueError, OSError):
        row = _row("Memory", True, "memory.unknown")
    else:
        ok = gib >= MIN_MEMORY_GIB * 0.95
        row = _row("Memory", ok, "memory.ok" if ok else "memory.low",
                   {"gib": f"{gib:.0f}", "min": MIN_MEMORY_GIB})
    row["optional"] = True
    return row


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
    return [_llama(), _scanner(), _shared(install.BASE, "Base model"),
            _shared(install.ORCHESTRATOR, "Orchestrator model"), _memory(), _git(),
            _orphans(scanning)]
