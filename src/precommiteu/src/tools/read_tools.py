from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from precommiteu.src.chunk_view import CanonicalChunk
from precommiteu.src.file_filter import CODE_EXTENSIONS, is_code_file
from precommiteu.src.ignore_directives import apply_prompt_ignore_directives
from precommiteu.src.tools.sandbox import Sandbox

__all__ = [
    "read_file",
    "read_chunk",
    "list_chunks",
    "list_dir",
    "glob",
    "grep",
]

_MAX_READ_LINES = 200
_MAX_GREP_LINES_DEFAULT = 50
_MAX_LIST_DIR_ENTRIES = 1000
_GREP_TIMEOUT_S = 10.0

_SECRET_DIRS = frozenset({".git"})
_SECRET_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx", ".log"})


# A recognized code extension wins: id_generator.py and credential_service.py are
# source worth scanning, while id_rsa and credentials.json are not.
def _is_sensitive(path: Path) -> bool:
    if _SECRET_DIRS.intersection(path.parts):
        return True
    name = path.name.lower()
    if name.startswith(".env"):
        return True
    if path.suffix.lower() in _SECRET_SUFFIXES:
        return True
    if path.suffix.lower() in CODE_EXTENSIONS:
        return False
    return name.startswith("id_") or "credential" in name or "secret" in name


# Tools read raw bytes, so eu-ignore directives must be honored here too:
# enforcing them only at prompt assembly lets the model read back what the
# user suppressed, and quote it as evidence for a confirmed finding.
def _readable_text(path: Path) -> str | None:
    return apply_prompt_ignore_directives(
        path.read_text(encoding="utf-8", errors="replace")
    )


def _line_numbered(lines: list[str], start_line: int) -> str:
    out: list[str] = []
    for offset, line in enumerate(lines):
        out.append(f"{start_line + offset:>4} | {line}")
    return "\n".join(out)


def read_file(
    sandbox: Sandbox,
    path: str,
    start_line: int = 1,
    end_line: int = 200,
) -> dict[str, Any]:
    resolved = sandbox.resolve(path)
    if _is_sensitive(resolved):
        raise PermissionError(f"{resolved.name} is excluded: it may hold secrets")
    text = _readable_text(resolved)
    if text is None:
        return {
            "path": str(resolved),
            "start_line": start_line,
            "end_line": start_line - 1,
            "text": "",
            "warning": "file excluded by eu-ignore-file",
        }
    all_lines = text.splitlines()
    total = len(all_lines)
    if start_line < 1:
        start_line = 1
    if end_line < start_line:
        end_line = start_line
    end_line = min(end_line, start_line + _MAX_READ_LINES - 1, total)
    if start_line > total:
        return {
            "path": str(resolved),
            "start_line": start_line,
            "end_line": start_line - 1,
            "text": "",
        }
    selected = all_lines[start_line - 1 : end_line]
    return {
        "path": str(resolved),
        "start_line": start_line,
        "end_line": end_line,
        "text": _line_numbered(selected, start_line),
    }


def read_chunk(
    sandbox: Sandbox,
    chunks: list[CanonicalChunk],
    path: str,
    chunk_id: str,
) -> dict[str, Any]:
    resolved = sandbox.resolve(path)
    for chunk in chunks:
        if chunk.id == chunk_id:
            return {
                "path": str(resolved),
                "chunk_id": chunk.id,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "text": chunk.text,
            }
    raise ValueError(f"unknown chunk_id: {chunk_id}")


def list_chunks(
    chunks: list[CanonicalChunk],
    path: str,
) -> list[dict[str, Any]]:
    return [
        {
            "id": c.id,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "n_chars": len(c.text),
        }
        for c in chunks
        if c.file == path or Path(c.file).name == Path(path).name
    ] or [
        {
            "id": c.id,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "n_chars": len(c.text),
        }
        for c in chunks
    ]


def list_dir(
    sandbox: Sandbox,
    path: str,
    depth: int = 1,
) -> dict[str, Any]:
    resolved = sandbox.resolve(path)
    if not resolved.is_dir():
        return {"path": str(resolved), "entries": [], "warning": "not a directory"}
    root = sandbox.roots[0]
    entries: list[dict[str, Any]] = []

    def walk(p: Path, current_depth: int) -> None:
        if len(entries) >= _MAX_LIST_DIR_ENTRIES:
            return
        try:
            children = sorted(p.iterdir(), key=lambda x: x.name)
        except OSError:
            return
        for child in children:
            if len(entries) >= _MAX_LIST_DIR_ENTRIES:
                return
            if _is_sensitive(child):
                continue
            is_dir = child.is_dir()
            if not is_dir:
                if child.suffix and not is_code_file(child, root):
                    continue
            entries.append(
                {
                    "path": str(child),
                    "is_dir": is_dir,
                }
            )
            if is_dir and current_depth < depth:
                walk(child, current_depth + 1)

    walk(resolved, 1)
    return {"path": str(resolved), "entries": entries}


def glob(sandbox: Sandbox, pattern: str) -> dict[str, Any]:
    root = sandbox.roots[0]
    matches: list[str] = []
    for match in root.glob(pattern):
        if _is_sensitive(match):
            continue
        try:
            sandbox.resolve(str(match))
        except PermissionError:
            continue
        matches.append(str(match))
        if len(matches) >= _MAX_LIST_DIR_ENTRIES:
            break
    return {"root": str(root), "pattern": pattern, "matches": matches}


# Model-supplied patterns run in a subprocess: Python's re has no timeout,
# so a catastrophic-backtracking pattern must be killable.
_GREP_WORKER = """\
import json, pathlib, re, sys

from precommiteu.src.ignore_directives import apply_prompt_ignore_directives

req = json.load(sys.stdin)
regex = re.compile(req["pattern"])
results = []
for p in req["paths"]:
    if len(results) >= req["cap"]:
        break
    try:
        text = pathlib.Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    text = apply_prompt_ignore_directives(text)
    if text is None:
        continue
    for lineno, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            results.append({"path": p, "line": lineno, "text": line})
            if len(results) >= req["cap"]:
                break
print(json.dumps(results))
"""


def grep(
    sandbox: Sandbox,
    pattern: str,
    path: str = ".",
    file_glob: str = "**/*",
    max_lines: int = _MAX_GREP_LINES_DEFAULT,
) -> dict[str, Any]:
    if path == ".":
        base = sandbox.roots[0]
    else:
        base = sandbox.resolve(path)
    try:
        re.compile(pattern)
    except re.error as exc:
        return {"pattern": pattern, "error": f"invalid regex: {exc}", "results": []}
    cap = max(1, min(max_lines, _MAX_GREP_LINES_DEFAULT))
    candidates: list[Path]
    if base.is_file():
        candidates = [base]
    else:
        candidates = sorted(base.glob(file_glob))
    vetted: list[str] = []
    for f in candidates:
        if not f.is_file() or _is_sensitive(f):
            continue
        try:
            sandbox.resolve(str(f))
        except PermissionError:
            continue
        vetted.append(str(f))

    worker = subprocess.Popen(
        [sys.executable, "-c", _GREP_WORKER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    request = json.dumps({"pattern": pattern, "paths": vetted, "cap": cap})
    try:
        out, _ = worker.communicate(request, timeout=_GREP_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        worker.kill()
        worker.communicate()
        return {
            "pattern": pattern,
            "error": f"grep timed out after {_GREP_TIMEOUT_S:.0f}s. "
            "use a simpler pattern",
            "results": [],
        }
    if worker.returncode != 0:
        return {"pattern": pattern, "error": "grep failed", "results": []}
    results = json.loads(out)
    return {"pattern": pattern, "results": results, "capped": len(results) >= cap}
