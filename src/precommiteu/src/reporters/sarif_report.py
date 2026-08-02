from __future__ import annotations

import json
import pathlib

from precommiteu.src.sarif import findings_to_sarif
from precommiteu.src.schemas import ScanResult

__all__ = ["write_sarif_report"]


def write_sarif_report(result: ScanResult, path: pathlib.Path) -> None:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = findings_to_sarif(result.findings)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
