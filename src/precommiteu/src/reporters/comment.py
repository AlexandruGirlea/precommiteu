from __future__ import annotations

import pathlib

from precommiteu.src.regulations import (
    article_display_label,
    article_url,
    regulation_display_name,
)
from precommiteu.src.schemas import Finding, ScanResult

__all__ = ["write_comment", "render_comment"]


def _article_link(article_id: str | None) -> str:
    if not article_id:
        return "n/a"
    label = article_display_label(article_id) or article_id
    url = article_url(article_id)
    if url:
        return f"[{label}]({url})"
    return label


def _location(f: Finding) -> str:
    file = f.file or "<unknown>"
    if f.start_line is None:
        return file
    if f.end_line is None or f.end_line == f.start_line:
        return f"{file}:{f.start_line}"
    return f"{file}:{f.start_line}-{f.end_line}"


def _evidence_cell(f: Finding) -> str:
    raw = (f.code_evidence or "").strip()
    if not raw:
        return "n/a"
    one_line = " ".join(raw.split())
    if len(one_line) > 120:
        one_line = one_line[:117] + "..."
    return f"`{one_line}`"


def render_comment(result: ScanResult) -> str:
    findings = result.findings
    n = len(findings)
    header = "## precommitEU: regulatory scan\n"
    if n == 0:
        return header + "\nNo findings.\n"

    regs = sorted({f.regulation for f in findings})
    regs_label = ", ".join(regulation_display_name(r) for r in regs)
    summary = f"\n**{n} finding{'s' if n != 1 else ''}** across {regs_label}.\n\n"

    rows = ["| Location | Article | Evidence | Description |", "| --- | --- | --- | --- |"]
    for f in findings:
        loc = _location(f)
        article = _article_link(f.probable_article_id)
        evidence = _evidence_cell(f)
        desc = (f.description or "").replace("|", "\\|")
        rows.append(f"| {loc} | {article} | {evidence} | {desc} |")
    return header + summary + "\n".join(rows) + "\n"


def write_comment(result: ScanResult, path: pathlib.Path) -> None:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_comment(result), encoding="utf-8")
