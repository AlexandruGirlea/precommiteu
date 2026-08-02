from __future__ import annotations

import re

_DIRECTIVE_BOUNDARY = r"(?<![A-Za-z0-9_-]){name}(?![A-Za-z0-9_-])"
_IGNORE_FILE_RE = re.compile(_DIRECTIVE_BOUNDARY.format(name="eu-ignore-file"))
_IGNORE_NEXT_LINE_RE = re.compile(_DIRECTIVE_BOUNDARY.format(name="eu-ignore-next-line"))
_IGNORE_NEXT_LINES_RE = re.compile(
    _DIRECTIVE_BOUNDARY.format(name="eu-ignore-next-lines")
    + r"\s*(?::|=)\s*(\d+)"
)
_IGNORE_START_RE = re.compile(_DIRECTIVE_BOUNDARY.format(name="eu-ignore-start"))
_IGNORE_END_RE = re.compile(_DIRECTIVE_BOUNDARY.format(name="eu-ignore-end"))
_IGNORE_RE = re.compile(_DIRECTIVE_BOUNDARY.format(name="eu-ignore"))


def has_prompt_ignore_file_directive(source_text: str) -> bool:
    return bool(_IGNORE_FILE_RE.search(source_text))


def apply_prompt_ignore_directives(source_text: str) -> str | None:
    if has_prompt_ignore_file_directive(source_text):
        return None

    lines = source_text.splitlines(keepends=True)
    if not lines:
        return source_text

    is_diff = looks_like_unified_diff(lines)
    remove_next = 0
    in_block = False
    filtered: list[str] = []
    for line in lines:
        if is_diff and line.startswith("diff --git "):
            remove_next = 0
            in_block = False
        starts = bool(_IGNORE_START_RE.search(line))
        ends = bool(_IGNORE_END_RE.search(line))
        if starts or ends:
            filtered.append(_blank_line(line))
            # Both on one line open and close immediately; treating it as a
            # bare start would silently blank the rest of the file.
            if starts != ends:
                in_block = starts
            continue
        if in_block and _is_next_line_target(line, is_diff=is_diff):
            filtered.append(_blank_line(line))
            continue
        if remove_next and _is_next_line_target(line, is_diff=is_diff):
            filtered.append(_blank_line(line))
            remove_next -= 1
            continue
        next_lines = _IGNORE_NEXT_LINES_RE.search(line)
        if next_lines:
            filtered.append(_blank_line(line))
            remove_next += int(next_lines.group(1))
            continue
        if _IGNORE_NEXT_LINE_RE.search(line):
            filtered.append(_blank_line(line))
            remove_next += 1
            continue
        if _IGNORE_RE.search(line):
            filtered.append(_blank_line(line))
            continue
        filtered.append(line)
    return "".join(filtered)


def _blank_line(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return "\n"


def looks_like_unified_diff(lines: list[str]) -> bool:
    # Both a hunk header and a file header are required: "diff --git " alone
    # occurs in ordinary source, and misreading a source file as a diff makes
    # every eu-ignore directive in it silently stop matching.
    head = lines[:100]
    return any(line.startswith("@@ ") for line in head) and any(
        line.startswith(("diff --git ", "--- ", "+++ ")) for line in head
    )


def _is_next_line_target(line: str, *, is_diff: bool) -> bool:
    if not is_diff:
        return True
    if line.startswith(("+++", "---")):
        return False
    return line.startswith(("+", "-", " "))
