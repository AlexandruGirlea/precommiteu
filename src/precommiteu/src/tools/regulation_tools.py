from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from precommiteu.src.tools.sandbox import Sandbox

__all__ = ["list_articles", "read_article", "grep_regulation"]

_MAX_ARTICLE_CHARS = 6000
_MAX_GREP_LINES_DEFAULT = 50
_DEFAULT_REGULATION = "gdpr"


def _first_existing(*candidates: Path) -> Path:
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _summary_path(docs_dir: Path, regulation: str) -> Path:
    docs_dir = Path(docs_dir)
    return _first_existing(
        docs_dir / regulation / "regulations_summary.md",
        docs_dir / f"{regulation}_regulations_summary.md",
    )


def _full_path(docs_dir: Path, regulation: str) -> Path:
    docs_dir = Path(docs_dir)
    return _first_existing(
        docs_dir / regulation / "full_regulations.md",
        docs_dir / f"{regulation}_full_regulations.md",
        docs_dir / regulation / "regulations_summary.md",
        docs_dir / f"{regulation}_regulations_summary.md",
    )


def _article_heading(regulation: str) -> re.Pattern[str]:
    return re.compile(rf"^##\s+({re.escape(regulation)}_art\d+)\s*$", re.MULTILINE)


def list_articles(
    sandbox: Sandbox,
    docs_dir: Path,
    regulation: str = _DEFAULT_REGULATION,
) -> list[str]:
    path = sandbox.resolve(str(_summary_path(docs_dir, regulation)))
    text = path.read_text(encoding="utf-8")
    return [m.group(1) for m in _article_heading(regulation).finditer(text)]


def read_article(
    sandbox: Sandbox,
    docs_dir: Path,
    article_id: str,
    summary: bool = False,
    regulation: str = _DEFAULT_REGULATION,
) -> dict[str, Any]:
    source_path = (
        _summary_path(docs_dir, regulation)
        if summary
        else _full_path(docs_dir, regulation)
    )
    path = sandbox.resolve(str(source_path))
    text = path.read_text(encoding="utf-8")
    matches = list(_article_heading(regulation).finditer(text))
    start_idx: int | None = None
    end_idx: int | None = None
    for i, m in enumerate(matches):
        if m.group(1) == article_id:
            start_idx = m.start()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            break
    if start_idx is None or end_idx is None:
        raise ValueError(f"unknown article_id: {article_id}")
    slice_text = text[start_idx:end_idx]
    truncated = False
    if len(slice_text) > _MAX_ARTICLE_CHARS:
        slice_text = slice_text[:_MAX_ARTICLE_CHARS]
        truncated = True
    return {
        "article_id": article_id,
        "source": "summary" if summary else "full",
        "path": str(path),
        "text": slice_text,
        "truncated": truncated,
    }


def grep_regulation(
    sandbox: Sandbox,
    docs_dir: Path,
    pattern: str,
    max_lines: int = _MAX_GREP_LINES_DEFAULT,
    regulation: str = _DEFAULT_REGULATION,
) -> dict[str, Any]:
    path = sandbox.resolve(str(_full_path(docs_dir, regulation)))
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return {"pattern": pattern, "error": f"invalid regex: {exc}", "results": []}
    text = path.read_text(encoding="utf-8")
    cap = max(1, min(max_lines, _MAX_GREP_LINES_DEFAULT))
    results: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            results.append({"line": lineno, "text": line})
            if len(results) >= cap:
                break
    return {
        "pattern": pattern,
        "path": str(path),
        "results": results,
        "capped": len(results) >= cap,
    }
