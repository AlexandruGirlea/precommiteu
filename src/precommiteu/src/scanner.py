from __future__ import annotations

import re
from typing import Any

from precommiteu.src.schemas import Finding

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")
_ARTICLE_NUMBER_RE = re.compile(r"(?:^|_)(?:art|article)_?(\d+)(?:_|$)")
_EVIDENCE_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+")
_EVIDENCE_MIN_NONSPACE_CHARS = 6
_EVIDENCE_MIN_TOKENS = 2


def _squash_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _normalize_validator_article_id(raw_article_id: str, regulation: str) -> str:
    reg_prefix = regulation.replace("-", "_").lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", raw_article_id.strip().lower()).strip("_")
    if not normalized:
        return ""

    match = _ARTICLE_NUMBER_RE.search(normalized)
    if match and (
        normalized.startswith(reg_prefix)
        or normalized.startswith("art")
        or normalized.startswith("article")
    ):
        return f"{reg_prefix}_art{match.group(1)}"
    return normalized


def _current_code_from_chunk(text: str) -> str:
    lines = text.splitlines()
    # Deliberately looser than looks_like_unified_diff: a chunk is a slice of a
    # file, so a mid-diff chunk carries hunk lines with no file header above it.
    is_diff = any(
        line.startswith(("diff --git ", "@@ "))
        for line in lines
    )
    if not is_diff:
        return text

    current_lines: list[str] = []
    for line in lines:
        if line.startswith(("diff --git ", "index ", "--- ", "+++ ", "@@ ")):
            continue
        if line.startswith("-"):
            continue
        if line.startswith(("+", " ")):
            current_lines.append(line[1:])
        else:
            current_lines.append(line)
    return "\n".join(current_lines)


def _validator_evidence_specific_enough(evidence: str) -> bool:
    compact_evidence = re.sub(r"\s+", "", evidence)
    if len(compact_evidence) < _EVIDENCE_MIN_NONSPACE_CHARS:
        return False

    tokens = set(_EVIDENCE_TOKEN_RE.findall(evidence))
    if len(tokens) >= _EVIDENCE_MIN_TOKENS:
        return True

    return any(char in evidence for char in ("(", ")", "=", ".", "\"", "'", "/", ":", "[", "]"))


def _validator_evidence_visible(evidence: str, chunk_text: str) -> bool:
    if not _validator_evidence_specific_enough(evidence):
        return False

    normalized_evidence = _squash_whitespace(evidence)
    if not normalized_evidence:
        return False

    current_code = _current_code_from_chunk(chunk_text)
    if normalized_evidence in _squash_whitespace(current_code):
        return True

    alnum_evidence = _NON_ALNUM_RE.sub("", evidence)
    return len(alnum_evidence) >= 6 and alnum_evidence in _NON_ALNUM_RE.sub("", current_code)


def _finding_key(finding: Finding) -> tuple[Any, ...]:
    return (
        finding.regulation,
        finding.probable_article_id,
        finding.file,
        finding.start_line,
        finding.end_line,
        finding.description.strip().lower(),
    )


def dedup_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[Any, ...]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = _finding_key(finding)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
