from __future__ import annotations

import re

_DETECTOR_FINDINGS_RE = re.compile(r"<findings>(.+?)</findings>", re.DOTALL)


def _extract_detector_findings_json(raw: str) -> str:
    match = _DETECTOR_FINDINGS_RE.search(raw)
    if not match:
        raise ValueError(
            "Model output missing <findings>...</findings> block. "
            "Grammar may not have been applied; ensure llama.cpp received the "
            "compiled DETECTOR_GBNF."
        )
    return match.group(1).strip()
