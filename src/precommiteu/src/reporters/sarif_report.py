from __future__ import annotations

import html
import json
import pathlib

from precommiteu.src.sarif import findings_to_sarif
from precommiteu.src.schemas import ScanResult

__all__ = ["write_sarif_report"]


def write_sarif_report(result: ScanResult, path: pathlib.Path) -> None:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = findings_to_sarif(result.findings)
    incomplete = [s for s in result.statuses if s.status != "scanned"]
    payload["runs"][0]["invocations"] = [{
        "executionSuccessful": not incomplete,
        "toolExecutionNotifications": [
            {
                "level": "error" if s.status == "failed" else "warning",
                "message": {
                    "text": html.escape(
                        f"{s.regulation}: {s.status}"
                        + (f" — {s.detail}" if s.detail else "")
                    ),
                },
            }
            for s in incomplete
        ],
    }]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
