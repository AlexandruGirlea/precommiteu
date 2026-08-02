from __future__ import annotations

import pathlib
import re

from precommiteu.config import (
    CHARS_PER_TOKEN,
    CHUNK_TARGET_MAX_TOKENS,
    CHUNK_TARGET_MIN_TOKENS,
    USER_MESSAGE_TOKEN_BUDGET,
)
from precommiteu.src.chunk_view import CanonicalChunk

__all__ = [
    "APPROX_TOKENS",
    "USER_MESSAGE_TOKEN_BUDGET",
    "CanonicalChunk",
    "token_chunks",
    "truncate_to_token_budget",
]

_TRUNCATION_MARKER = "\n[...TRUNCATED...]"

_BOUNDARY_RE = re.compile(r"^(?:def |class |async def |\s*$)")


def APPROX_TOKENS(text: str) -> int:
    return max(1, int(len(text) // CHARS_PER_TOKEN))


def truncate_to_token_budget(text: str, budget_tokens: int) -> str:
    if APPROX_TOKENS(text) <= budget_tokens:
        return text
    max_chars = int(budget_tokens * CHARS_PER_TOKEN) - len(_TRUNCATION_MARKER)
    if max_chars <= 0:
        return _TRUNCATION_MARKER.strip()
    return text[:max_chars] + _TRUNCATION_MARKER


def token_chunks(path: pathlib.Path, text: str) -> list[CanonicalChunk]:
    file_str = str(path)
    lines = text.splitlines(keepends=True)
    if not lines:
        return []

    out: list[CanonicalChunk] = []
    n = len(lines)
    i = 0
    start_line = 1

    while i < n:
        buf_start = i
        running_chars = 0
        last_boundary_after_min: int | None = None
        cut_at: int | None = None

        while i < n:
            ln = lines[i]
            next_chars = running_chars + len(ln)
            next_tokens = max(1, int(next_chars // CHARS_PER_TOKEN))

            if next_tokens > CHUNK_TARGET_MAX_TOKENS:
                if last_boundary_after_min is not None:
                    cut_at = last_boundary_after_min
                else:
                    cut_at = i if i > buf_start else buf_start + 1
                break

            running_chars = next_chars
            i += 1

            if (
                next_tokens >= CHUNK_TARGET_MIN_TOKENS
                and i < n
                and _BOUNDARY_RE.match(lines[i])
            ):
                last_boundary_after_min = i

        if cut_at is None:
            cut_at = n

        cut_at = max(cut_at, buf_start + 1)
        chunk_text_str = "".join(lines[buf_start:cut_at])
        end_line = start_line + (cut_at - buf_start) - 1
        out.append(
            CanonicalChunk(
                id=f"{file_str}:{start_line}-{end_line}",
                file=file_str,
                start_line=start_line,
                end_line=end_line,
                text=chunk_text_str,
            )
        )
        start_line = end_line + 1
        i = cut_at

    return out
