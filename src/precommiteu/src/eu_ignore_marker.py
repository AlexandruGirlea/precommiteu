from __future__ import annotations

import fnmatch
import re
import sys
from dataclasses import dataclass

from precommiteu.src.ignore_directives import looks_like_unified_diff

_MARKER_RE = re.compile(
    r'precommiteu-ignore:\s*'
    r'([A-Za-z0-9_*?\-\.]+)\s+'
    r'reason\s*=\s*(["\'])((?:(?!\2).)*)\2'
)
_WILDCARD_ONLY_RE = re.compile(r'^[*?]+$')
_HUNK_RE = re.compile(
    r"@@\s+-\d+(?:,\d+)?\s+\+(?P<start>\d+)(?:,\d+)?\s+@@"
)


@dataclass(frozen=True)
class EuIgnoreMarker:
    rule: str
    reason: str
    line_no: int


def parse_eu_ignore_markers(source_text: str) -> list[EuIgnoreMarker]:
    markers: list[EuIgnoreMarker] = []
    for line_no, line in enumerate(source_text.splitlines(), start=1):
        markers.extend(_parse_eu_ignore_marker_line(line, line_no))
    return markers


def parse_eu_ignore_markers_in_unified_diff(diff_text: str) -> list[EuIgnoreMarker]:
    markers: list[EuIgnoreMarker] = []
    current_new_line: int | None = None
    for line in diff_text.splitlines():
        if line.startswith("@@ "):
            match = _HUNK_RE.match(line)
            current_new_line = int(match.group("start")) if match else None
            continue
        if current_new_line is None:
            continue
        if line.startswith(("+", " ")):
            markers.extend(_parse_eu_ignore_marker_line(line[1:], current_new_line))
            current_new_line += 1
        elif line.startswith(("-", "\\")):
            continue
        else:
            markers.extend(_parse_eu_ignore_marker_line(line, current_new_line))
            current_new_line += 1
    return markers


def parse_eu_ignore_markers_for_scan_text(source_text: str) -> list[EuIgnoreMarker]:
    if looks_like_unified_diff(source_text.splitlines()):
        return parse_eu_ignore_markers_in_unified_diff(source_text)
    return parse_eu_ignore_markers(source_text)


def _parse_eu_ignore_marker_line(line: str, line_no: int) -> list[EuIgnoreMarker]:
    markers: list[EuIgnoreMarker] = []
    for match in _MARKER_RE.finditer(line):
        rule, reason = match.group(1), match.group(3).strip()
        if not reason:
            continue
        if _WILDCARD_ONLY_RE.match(rule):
            print(
                f"::warning::precommitEU: inline wildcard marker "
                f'`precommiteu-ignore: {rule}` rejected at line {line_no} '
                "(wildcard inline ignores are not supported).",
                file=sys.stderr,
            )
            continue
        markers.append(EuIgnoreMarker(rule=rule, reason=reason, line_no=line_no))
    return markers


def match_eu_ignore_marker_in_range(
    article_id: str | None,
    start_line: int | None,
    end_line: int | None,
    markers: list[EuIgnoreMarker],
    *,
    radius: int = 2,
) -> EuIgnoreMarker | None:
    if not article_id:
        return None
    line_bounds = [line for line in (start_line, end_line) if line is not None]
    if not line_bounds:
        return None
    low = min(line_bounds) - radius
    high = max(line_bounds) + radius
    for marker in markers:
        if not (low <= marker.line_no <= high):
            continue
        if _rule_matches(article_id, marker.rule):
            return marker
    return None


def _rule_matches(article_id: str, rule: str) -> bool:
    return rule == "*" or fnmatch.fnmatchcase(article_id, rule)
