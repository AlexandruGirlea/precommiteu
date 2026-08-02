from __future__ import annotations

import logging
import os
import pathlib
import sys
from collections.abc import Callable
from typing import Any

from precommiteu.src.reporters import (
    write_comment,
    write_json_report,
    write_sarif_report,
)
from precommiteu.src.scanner import dedup_findings
from precommiteu.src.schemas import Advisory, Finding, ScanResult

__all__ = ["IncrementalReporter", "attach_scan_log", "log_scan_event"]

_EVENT_LOG = logging.getLogger("precommiteu.events")


def attach_scan_log(path: pathlib.Path) -> None:
    try:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, mode="a", encoding="utf-8")
    except OSError as exc:
        print(
            f"::warning::precommiteu: cannot open log file {path} ({exc}); "
            "continuing without file logging.",
            file=sys.stderr,
        )
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger = logging.getLogger("precommiteu")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def log_scan_event(payload: dict[str, Any]) -> None:
    event = str(payload.get("event", "progress"))
    details = [f"{k}={v!r}" for k, v in payload.items() if k != "event"]
    _EVENT_LOG.info(" ".join([event, *details]))


def _atomic_write(
    writer: Callable[[ScanResult, pathlib.Path], None],
    result: ScanResult,
    path: pathlib.Path,
) -> None:
    path = pathlib.Path(path)
    # Unique suffix: a fixed ".tmp" would clobber a same-named user file.
    tmp = path.with_name(f"{path.name}.precommiteu_tmp_{os.getpid()}")
    try:
        writer(result, tmp)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


class IncrementalReporter:
    def __init__(
        self,
        *,
        json_out: pathlib.Path | None = None,
        sarif: pathlib.Path | None = None,
        out: pathlib.Path | None = None,
    ) -> None:
        self._json_out = json_out
        self._sarif = sarif
        self._out = out
        self._findings: list[Finding] = []
        self._advisories: list[Advisory] = []

    def add_finding(self, finding: Finding) -> None:
        self._findings.append(finding)

    def add_advisory(self, advisory: Advisory) -> None:
        self._advisories.append(advisory)

    def snapshot(self) -> None:
        self._write_all(
            ScanResult(
                findings=dedup_findings(self._findings),
                statuses=[],
                advisories=list(self._advisories),
            )
        )

    def finalize(self, result: ScanResult) -> None:
        self._write_all(result)

    def _write_all(self, result: ScanResult) -> None:
        if self._json_out is not None:
            _atomic_write(write_json_report, result, self._json_out)
        if self._sarif is not None:
            _atomic_write(write_sarif_report, result, self._sarif)
        if self._out is not None:
            _atomic_write(write_comment, result, self._out)
