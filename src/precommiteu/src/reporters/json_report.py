from __future__ import annotations

import json
import pathlib

from precommiteu.src.schemas import ScanResult

__all__ = ["write_json_report"]


def write_json_report(result: ScanResult, path: pathlib.Path) -> None:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
