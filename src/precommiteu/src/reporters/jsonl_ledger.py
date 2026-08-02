from __future__ import annotations

import json
import os
import pathlib
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TextIO

__all__ = ["jsonl_ledger", "LedgerWriter"]


class LedgerWriter:
    def __init__(self, fh: TextIO) -> None:
        self._fh = fh

    def write(self, event: str, **payload: Any) -> None:
        record = {
            "event": event,
            "ts": time.time(),
            "payload": payload,
        }
        line = json.dumps(record, ensure_ascii=False)
        self._fh.write(line + "\n")
        self._fh.flush()
        try:
            os.fsync(self._fh.fileno())
        except (OSError, AttributeError, ValueError):
            pass


@contextmanager
def jsonl_ledger(path: pathlib.Path | str) -> Iterator[LedgerWriter]:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fh = p.open("a", encoding="utf-8")
    try:
        yield LedgerWriter(fh)
    finally:
        try:
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except (OSError, AttributeError, ValueError):
                pass
        finally:
            fh.close()
