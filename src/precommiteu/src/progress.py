from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any, Literal

__all__ = ["make_progress_emitter", "ProgressMode"]

ProgressMode = Literal["text", "jsonl", "none"]


def _text_line(payload: dict[str, Any]) -> str:
    event = payload.get("event", "?")
    file = payload.get("file")
    extras: list[str] = []
    interesting = (
        "regulation",
        "adapter",
        "candidates",
        "kept",
        "kept_raw",
        "files_total",
        "findings_total",
        "exit_reason",
    )
    for key in interesting:
        if key in payload and payload[key] is not None:
            extras.append(f"{key}={payload[key]}")
    extras_str = " ".join(extras)
    if file:
        return f"[{event}] {file} {extras_str}".rstrip()
    return f"[{event}] {extras_str}".rstrip()


def make_progress_emitter(mode: ProgressMode) -> Callable[[dict[str, Any]], None] | None:
    if mode == "none":
        return None
    if mode == "jsonl":
        def _emit(payload: dict[str, Any]) -> None:
            sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
            sys.stderr.flush()
        return _emit
    if mode == "text":
        def _emit_text(payload: dict[str, Any]) -> None:
            sys.stderr.write(_text_line(payload) + "\n")
            sys.stderr.flush()
        return _emit_text
    return None
