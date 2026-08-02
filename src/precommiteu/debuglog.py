from __future__ import annotations

import json
import os
from typing import Any

__all__ = ["validator_debug"]


def validator_debug(payload: dict[str, Any]) -> None:
    target = os.environ.get("PRECOMMITEU_DEBUG_VALIDATOR")
    if not target or target == "0":
        return
    path = "precommiteu_validator_debug.jsonl" if target == "1" else target
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
