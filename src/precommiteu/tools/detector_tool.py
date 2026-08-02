from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from precommiteu.detector_call import call_detector as _raw_call_detector
from precommiteu.regulations import RegulationPack
from precommiteu.tools.validator_tool import CandidatesStore

__all__ = ["build_call_detector_tool"]


def build_call_detector_tool(
    *,
    detector_model: Any,
    candidates_store: CandidatesStore,
    regulation_pack: RegulationPack,
    remaining_seconds: Callable[[], float] | None = None,
) -> Callable[..., str]:
    def call_detector(enriched_code: str, file_label: str) -> str:
        results = _raw_call_detector(
            enriched_code=enriched_code,
            model=detector_model,
            regulation_pack=regulation_pack,
            timeout_s=remaining_seconds() if remaining_seconds else None,
        )
        candidates_store.put(file_label, results)
        return json.dumps(results)

    return call_detector
