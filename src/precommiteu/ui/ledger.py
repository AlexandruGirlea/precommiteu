from __future__ import annotations

import json
import pathlib
import time
from collections.abc import Callable
from typing import Any

from precommiteu.ui import eta


# The scanner is sequential, so a file is finished when the next file_start
# arrives. Two of the three file_error sites never emit a file_done.
class LedgerFold:
    def __init__(self, on_file: Callable[[str, dict], None]) -> None:
        self.on_file = on_file
        self.current: dict[str, Any] | None = None
        self.interrupted = False
        self.adapter: str | None = None

    def _finalize(self) -> None:
        if self.current is None:
            return
        entry = self.current
        self.current = None
        entry["duration_s"] = time.monotonic() - entry.pop("_started")
        if entry["status"] == "running":
            if entry.get("error"):
                entry["status"] = "error"
            elif self.interrupted:
                entry["status"] = "interrupted"
            elif entry.get("exit_reason") in ("direct", "emit"):
                entry["status"] = "done"
            else:
                entry["status"] = "partial"
        self.on_file(entry.pop("file"), entry)

    def feed(self, record: dict) -> None:
        event = record.get("event")
        payload = record.get("payload") or {}

        if event == "detector_adapter":
            self.adapter = payload.get("adapter")
        elif event == "file_start":
            self._finalize()
            self.current = {
                "file": payload.get("file", "?"),
                "chunks": payload.get("chunks", 1) or 1,
                "route": "direct",
                "fell_back": False,
                "exit_reason": None,
                "kept": 0,
                "status": "running",
                "findings": [],
                "_started": time.monotonic(),
            }
        elif event == "file_reused":
            # No file_start/file_done for these, but their findings still come
            # through, so the entry has to be open when they arrive.
            self._finalize()
            self.current = {
                "file": payload.get("file", "?"),
                "kept": payload.get("kept", 0),
                "status": "cached",
                "findings": [],
                "_started": time.monotonic(),
            }
        elif event == "orchestrator_done" and self.current is not None:
            self.current.update(
                route=payload.get("route", "direct"),
                fell_back=bool(payload.get("fell_back")),
                exit_reason=payload.get("exit_reason"),
            )
        elif event == "finding":
            # Two records per finding: a progress event, then the object.
            finding = payload.get("finding")
            if finding is not None and self.current is not None:
                self.current["findings"].append(finding)
        elif event == "file_done":
            if self.current is not None:
                self.current["kept"] = payload.get("kept", 0)
            self._finalize()
        elif event == "file_ignored":
            if self.current is not None:
                self.current["status"] = "ignored"
            self._finalize()
        elif event == "file_error" and self.current is not None:
            self.current["error"] = payload.get("error")
        elif event == "scan_interrupted":
            self.interrupted = True
        elif event == "scan_done":
            self._finalize()

    def close(self) -> None:
        self._finalize()


def tail(path: pathlib.Path, offset: int) -> tuple[list[dict], int]:
    if not path.exists():
        return [], offset
    with path.open("rb") as handle:
        handle.seek(offset)
        blob = handle.read()
    cut = blob.rfind(b"\n")
    if cut < 0:
        return [], offset
    records = []
    for line in blob[: cut + 1].splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records, offset + cut + 1


def observe_timing(timing: dict, entry: dict) -> None:
    eta.observe(
        timing,
        entry["route"],
        entry["duration_s"],
        entry["chunks"],
        entry["fell_back"],
        entry.get("exit_reason") or "",
    )
