from __future__ import annotations

import logging

from precommiteu.chunking import USER_MESSAGE_TOKEN_BUDGET, truncate_to_token_budget
from precommiteu.regulations import RegulationPack
from precommiteu.src.inference import _extract_detector_findings_json
from precommiteu.src.schemas import ModelOutput

logger = logging.getLogger(__name__)

_RAW_PREVIEW_CHARS = 400


def call_detector(
    enriched_code: str,
    model,
    *,
    regulation_pack: RegulationPack,
    timeout_s: float | None = None,
) -> list[dict]:
    pack = regulation_pack
    enriched_code = truncate_to_token_budget(enriched_code, USER_MESSAGE_TOKEN_BUDGET)
    user_message = f"[CODE DIFF]\n{enriched_code}"

    messages = [
        {"role": "system", "content": pack.detector_system},
        {"role": "user", "content": user_message},
    ]

    response = model.invoke(messages, timeout_s=timeout_s)
    raw = getattr(response, "content", "") or ""

    try:
        json_str = _extract_detector_findings_json(raw)
        parsed = ModelOutput.model_validate_json(json_str)
    except Exception as exc:
        logger.warning(
            "detector parse failed (%s); raw[:%d]=%r",
            exc,
            _RAW_PREVIEW_CHARS,
            raw[:_RAW_PREVIEW_CHARS],
        )
        return []

    return [{"description": f.description} for f in parsed.findings]
