from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from precommiteu.src.ignore_directives import apply_prompt_ignore_directives
from precommiteu.tools.sandbox import Sandbox

__all__ = ["find_references"]

_MAX_HITS = 10
_FALLBACK_WINDOW = 40
_MAX_TOTAL_BYTES = 6000
_GLOB_PATTERNS: tuple[str, ...] = (
    "**/*.py",
    "**/*.js",
    "**/*.ts",
    "**/*.tsx",
    "**/*.jsx",
    "**/*.java",
    "**/*.kt",
    "**/*.go",
    "**/*.rs",
    "**/*.cpp",
    "**/*.cc",
    "**/*.c",
    "**/*.h",
    "**/*.hpp",
    "**/*.cs",
    "**/*.rb",
    "**/*.php",
    "**/*.swift",
    "**/*.scala",
)


def _candidate_files(repo_root: Path) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for pattern in _GLOB_PATTERNS:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            if path in seen:
                continue
            seen.add(path)
            out.append(path)
    return out


def _fallback_window(lines: list[str], lineno: int) -> tuple[int, int, str]:
    start = max(1, lineno - _FALLBACK_WINDOW)
    end = min(len(lines), lineno + _FALLBACK_WINDOW)
    return start, end, "fallback_window"


def _python_scope_for_hit(
    text: str, lines: list[str], lineno: int
) -> tuple[int, int, str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _fallback_window(lines, lineno)
    best: tuple[int, int, str] | None = None
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            continue
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if start is None or end is None:
            continue
        if start <= lineno <= end:
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            if best is None or (end - start) < (best[1] - best[0]):
                best = (start, end, kind)
    if best is None:
        return _fallback_window(lines, lineno)
    return best


def find_references(
    sandbox: Sandbox,
    symbol: str,
    repo_root: Path,
) -> list[dict[str, Any]]:
    symbol = symbol.strip()
    if not symbol:
        return []
    try:
        pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    except re.error:
        return []

    repo_root_resolved = Path(repo_root).expanduser().resolve()
    try:
        sandbox.resolve(str(repo_root_resolved))
    except PermissionError:
        return []

    results: list[dict[str, Any]] = []
    total_bytes = 0

    for path in _candidate_files(repo_root_resolved):
        if len(results) >= _MAX_HITS or total_bytes >= _MAX_TOTAL_BYTES:
            break
        try:
            sandbox.resolve(str(path))
        except PermissionError:
            continue
        try:
            text = apply_prompt_ignore_directives(
                path.read_text(encoding="utf-8", errors="replace")
            )
        except OSError:
            continue
        if text is None:
            continue
        lines = text.splitlines()
        is_python = path.suffix == ".py"
        seen_scopes: set[tuple[str, int, int]] = set()
        for lineno, line in enumerate(lines, start=1):
            if not pattern.search(line):
                continue
            if is_python:
                start, end, kind = _python_scope_for_hit(text, lines, lineno)
            else:
                start, end, kind = _fallback_window(lines, lineno)
            scope_key = (str(path), start, end)
            if scope_key in seen_scopes:
                continue
            seen_scopes.add(scope_key)
            snippet = "\n".join(lines[start - 1 : end])
            snippet_bytes = len(snippet.encode("utf-8"))
            if total_bytes + snippet_bytes > _MAX_TOTAL_BYTES:
                remaining = _MAX_TOTAL_BYTES - total_bytes
                if remaining <= 0:
                    break
                snippet = snippet.encode("utf-8")[:remaining].decode(
                    "utf-8", errors="ignore"
                )
                snippet_bytes = len(snippet.encode("utf-8"))
            results.append(
                {
                    "file": str(path),
                    "start_line": start,
                    "end_line": end,
                    "snippet": snippet,
                    "scope_kind": kind,
                }
            )
            total_bytes += snippet_bytes
            if len(results) >= _MAX_HITS or total_bytes >= _MAX_TOTAL_BYTES:
                break
    return results
