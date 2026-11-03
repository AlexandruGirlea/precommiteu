from __future__ import annotations

import pathlib
import re
from collections.abc import Callable

from precommiteu.config import (
    CHARS_PER_TOKEN,
    CHUNK_OVERLAP_RATIO,
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


def token_counter(model) -> Callable[[str], int]:
    if callable(getattr(type(model), "count_tokens", None)):
        return model.count_tokens
    return APPROX_TOKENS


def truncate_to_token_budget(
    text: str, budget_tokens: int, *, count_tokens=APPROX_TOKENS,
) -> str:
    if count_tokens(text) <= budget_tokens:
        return text
    if count_tokens is not APPROX_TOKENS:
        if count_tokens(_TRUNCATION_MARKER) > budget_tokens:
            raise ValueError("model input budget is too small for truncation")
        low, high = 0, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if count_tokens(text[:middle] + _TRUNCATION_MARKER) <= budget_tokens:
                low = middle
            else:
                high = middle - 1
        return text[:low] + _TRUNCATION_MARKER
    max_chars = int(budget_tokens * CHARS_PER_TOKEN) - len(_TRUNCATION_MARKER)
    if max_chars <= 0:
        return _TRUNCATION_MARKER.strip()
    return text[:max_chars] + _TRUNCATION_MARKER


def token_chunks(
    path: pathlib.Path, text: str, *, count_tokens=APPROX_TOKENS,
) -> list[CanonicalChunk]:
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
        if count_tokens(chunk_text_str) > CHUNK_TARGET_MAX_TOKENS:
            low, high = buf_start, cut_at
            while low < high:
                middle = (low + high + 1) // 2
                if count_tokens("".join(lines[buf_start:middle])) <= CHUNK_TARGET_MAX_TOKENS:
                    low = middle
                else:
                    high = middle - 1
            if low == buf_start:
                raise ValueError(f"{path}:{start_line}: line exceeds model input budget")
            cut_at = low
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
        if cut_at == n:
            break
        overlap_budget = int(count_tokens(chunk_text_str) * CHUNK_OVERLAP_RATIO)
        low, high = buf_start + 1, cut_at
        while low < high:
            middle = (low + high) // 2
            if count_tokens("".join(lines[middle:cut_at])) <= overlap_budget:
                high = middle
            else:
                low = middle + 1
        i = low
        start_line = i + 1

    return out
