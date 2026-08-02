from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from typing import Any

__all__ = ["parse_loop_step", "run_react_loop"]

_logger = logging.getLogger(__name__)

_ACTION_HEAD_RE = re.compile(
    r"^\s*ACTION:\s*"
    r"(?P<tool>[A-Za-z_][A-Za-z0-9_]*)"
    r"\s*\((?P<rest>.*)$",
    re.DOTALL,
)

_EMIT_RE = re.compile(
    r"^\s*EMIT\s*(?:\r?\n(?P<reason>.*))?\s*$",
    re.DOTALL,
)

# Tolerates observed grammar escapes: quoted keys and JSON-style ':' separators
# ('"file_label": "x"', '"file_label="x"'). Bare string values never match
# because the separator [=:] is required.
_KEY_RE = re.compile(r'\s*"?(?P<key>[A-Za-z_][A-Za-z0-9_]*)"?\s*[=:]\s*')
_INT_RE = re.compile(r"(?P<ival>-?\d+)")
_BOOL_RE = re.compile(r"(?P<bval>true|True|false|False)")


def _decode_json_string(raw: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            nxt = raw[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "r":
                out.append("\r")
            elif nxt == '"':
                out.append('"')
            elif nxt == "\\":
                out.append("\\")
            elif nxt == "/":
                out.append("/")
            elif nxt == "b":
                out.append("\b")
            elif nxt == "f":
                out.append("\f")
            elif nxt == "u" and i + 5 < len(raw):
                hex4 = raw[i + 2 : i + 6]
                try:
                    out.append(chr(int(hex4, 16)))
                    i += 6
                    continue
                except ValueError as exc:
                    raise ValueError(f"invalid unicode escape: \\u{hex4}") from exc
            else:
                raise ValueError(f"invalid escape: \\{nxt}")
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _scan_quoted_string(s: str, pos: int) -> tuple[str, int]:
    if pos >= len(s) or s[pos] != '"':
        raise ValueError(f"expected '\"' at offset {pos}")
    i = pos + 1
    out: list[str] = []
    while i < len(s):
        ch = s[i]
        if ch == "\\":
            if i + 1 >= len(s):
                raise ValueError("trailing backslash in string literal")
            out.append(ch)
            out.append(s[i + 1])
            i += 2
            continue
        if ch == '"':
            return _decode_json_string("".join(out)), i + 1
        out.append(ch)
        i += 1
    raise ValueError("unterminated string literal")


def _parse_args_with_terminator(s: str) -> tuple[dict[str, Any], int]:
    parsed: dict[str, Any] = {}
    pos = 0
    n = len(s)
    while pos < n and s[pos] in " \t\r\n":
        pos += 1
    if pos < n and s[pos] == ")":
        return parsed, pos + 1
    while pos < n:
        m = _KEY_RE.match(s, pos)
        if not m:
            raise ValueError(f"expected key=value near offset {pos}: {s[pos:pos+40]!r}")
        key = m.group("key")
        pos = m.end()
        if pos >= n:
            raise ValueError(f"missing value for key {key!r}")
        ch = s[pos]
        if ch == '"':
            value, pos = _scan_quoted_string(s, pos)
            parsed[key] = value
        else:
            mi = _INT_RE.match(s, pos)
            mb = _BOOL_RE.match(s, pos)
            if mb is not None and (mi is None or mb.end() >= mi.end()):
                parsed[key] = mb.group("bval").lower() == "true"
                pos = mb.end()
            elif mi is not None:
                parsed[key] = int(mi.group("ival"))
                pos = mi.end()
            else:
                raise ValueError(
                    f"unrecognized value for key {key!r} near: {s[pos:pos+40]!r}"
                )
        while pos < n and s[pos] in " \t\r\n":
            pos += 1
        if pos < n and s[pos] == ",":
            pos += 1
            while pos < n and s[pos] in " \t\r\n":
                pos += 1
            continue
        if pos < n and s[pos] == ")":
            return parsed, pos + 1
        if pos >= n:
            raise ValueError("unterminated argument list (missing ')')")
        raise ValueError(f"expected ',' or ')' near offset {pos}: {s[pos:pos+40]!r}")
    raise ValueError("unterminated argument list (missing ')')")


def parse_loop_step(s: str) -> dict[str, Any]:
    if s is None:
        raise ValueError("loop step is None")
    text = s.rstrip()
    m = _ACTION_HEAD_RE.match(text)
    if m:
        tool = m.group("tool")
        rest = m.group("rest")
        try:
            args, consumed = _parse_args_with_terminator(rest)
        except ValueError as exc:
            raise ValueError(f"could not parse args for {tool}(...): {exc}") from exc
        tail = rest[consumed:].lstrip(" \t")
        if tail.startswith("\r"):
            tail = tail[1:]
        if tail.startswith("\n"):
            tail = tail[1:]
        reason = tail.strip()
        return {"kind": "action", "tool": tool, "args": args, "reason": reason}
    m = _EMIT_RE.match(re.sub(r"^\s*ACTION:\s*", "", text))
    if m:
        reason = (m.group("reason") or "").strip()
        return {"kind": "emit", "reason": reason}
    raise ValueError(f"unrecognized loop step: {s!r}")


def _message_text(msg: Any) -> str:
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content
    return str(content)


def run_react_loop(
    model: Any,
    system_prompt: str,
    initial_user_message: str,
    tools_map: dict[str, Callable[..., Any]],
    max_iterations: int,
    wall_seconds: float,
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[list[dict[str, str]], str]:
    history: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_user_message},
    ]
    start = time.monotonic()
    consecutive_parse_failures = 0

    for _ in range(max_iterations):
        remaining = wall_seconds - (time.monotonic() - start)
        if remaining <= 0:
            # a failure burning the budget must not read as a clean timeout
            if consecutive_parse_failures:
                return history, "loop_step_failed"
            return history, "budget_exhausted_time"

        try:
            response = model.invoke(history, timeout_s=remaining)
        except Exception as exc:
            _logger.warning(
                "react_loop: model.invoke raised on attempt %d: %r",
                consecutive_parse_failures,
                exc,
            )
            consecutive_parse_failures += 1
            if consecutive_parse_failures >= 3:
                return history, "loop_step_failed"
            continue

        raw = _message_text(response).strip()

        try:
            step = parse_loop_step(raw)
        except ValueError as exc:
            _logger.warning(
                "react_loop: parse_loop_step failed on attempt %d: %r (raw=%r)",
                consecutive_parse_failures,
                exc,
                raw[:200],
            )
            consecutive_parse_failures += 1
            if consecutive_parse_failures >= 3:
                return history, "loop_step_failed"
            continue

        consecutive_parse_failures = 0

        if on_step is not None:
            on_step(step)

        if step["kind"] == "emit":
            history.append({"role": "assistant", "content": raw})
            return history, "emit"

        history.append({"role": "assistant", "content": raw})

        tool = tools_map.get(step["tool"])
        if tool is None:
            tool_result = f"ERROR: unknown tool {step['tool']!r}"
        else:
            try:
                tool_result = tool(**step["args"])
            except Exception as exc:
                tool_result = f"ERROR: {type(exc).__name__}: {exc}"

        if not isinstance(tool_result, str):
            tool_result = str(tool_result)
        history.append({"role": "user", "content": tool_result})

    return history, "budget_exhausted_iters"
