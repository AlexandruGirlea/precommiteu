from __future__ import annotations

import json
import pathlib
import time
from typing import Any

from precommiteu.ui import settings

SEED_TIMING = {
    "c_direct": 14.0,
    "n_direct": 0,
    "c_orch": 55.0,
    "n_orch": 0,
    "cold_start_sec": 40.0,
}


def path_for(regulation: str) -> pathlib.Path:
    return settings.STATE_DIR / f"state-{regulation}.json"


def empty(target: str, regulation: str) -> dict[str, Any]:
    return {
        "target": target,
        "regulation": regulation,
        "timing": dict(SEED_TIMING),
        "files": {},
        "advisories": [],
        "run": None,
    }


def load(regulation: str) -> dict[str, Any]:
    try:
        return json.loads(path_for(regulation).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty("", regulation)


def save(state: dict[str, Any]) -> None:
    settings.write_json(path_for(state["regulation"]), state)


def next_segment(run_dir: pathlib.Path) -> str:
    run_dir.mkdir(parents=True, exist_ok=True)
    used = [int(p.name[1:4]) for p in run_dir.glob("s[0-9][0-9][0-9]*")]
    return f"s{max(used, default=0) + 1:03d}_{time.strftime('%d-%m-%Y_%H-%M')}"
