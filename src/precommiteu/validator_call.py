from __future__ import annotations

import json
import logging
import os
import sys

from precommiteu.chunking import (
    APPROX_TOKENS,
    USER_MESSAGE_TOKEN_BUDGET,
    truncate_to_token_budget,
)
from precommiteu.config import CANDIDATE_FINDINGS_TOKEN_BUDGET
from precommiteu.debuglog import validator_debug
from precommiteu.regulations import RegulationPack
from precommiteu.src.schemas import ValidatorOutput

logger = logging.getLogger(__name__)

_DEBUG_ENRICH = bool(os.environ.get("PRECOMMITEU_DEBUG_ENRICH"))
_RAW_PREVIEW_CHARS = 400

def call_validator(
    candidates: list[dict],
    enriched_code: str,
    file_label: str,
    model,
    *,
    regulation_pack: RegulationPack,
    timeout_s: float | None = None,
) -> list[dict]:
    if not candidates:
        return []

    pack = regulation_pack

    enriched_code = truncate_to_token_budget(
        enriched_code,
        USER_MESSAGE_TOKEN_BUDGET - CANDIDATE_FINDINGS_TOKEN_BUDGET,
    )

    candidates_json = json.dumps(
        {
            "candidates": [
                {"description": (c.get("description") or "").strip()}
                for c in candidates
            ],
        },
        ensure_ascii=False,
    )
    user_message = (
        f"<code_or_diff>\n{enriched_code}\n</code_or_diff>\n\n"
        f"<candidate_findings>\n{candidates_json}\n</candidate_findings>"
    )

    messages = [
        {"role": "system", "content": pack.validator_system},
        {"role": "user", "content": user_message},
    ]

    if _DEBUG_ENRICH:
        try:
            sys.stderr.write(
                "PRECOMMITEU_DEBUG_ENRICH "
                + json.dumps(
                    {
                        "event": "call_validator",
                        "file_label": file_label,
                        "user_message_chars": len(user_message),
                        "user_message_tokens": APPROX_TOKENS(user_message),
                        "enriched_code_chars": len(enriched_code),
                        "enriched_code_tokens": APPROX_TOKENS(enriched_code),
                        "candidates_count": len(candidates),
                    }
                )
                + "\n"
            )
            sys.stderr.flush()
        except Exception:
            pass

    response = model.invoke(messages, timeout_s=timeout_s)
    raw = getattr(response, "content", "") or ""

    try:
        parsed = ValidatorOutput.model_validate_json(raw)
        kept = [
            {
                "article_no": f.article_no,
                "code_evidence": f.code_evidence,
                "description": f.description,
            }
            for f in parsed.findings
        ]
    except Exception as exc:
        logger.warning(
            "validator parse failed (%s); raw[:%d]=%r",
            exc,
            _RAW_PREVIEW_CHARS,
            raw[:_RAW_PREVIEW_CHARS],
        )
        validator_debug(
            {
                "stage": "slm",
                "file_label": file_label,
                "candidates_in": [
                    (c.get("description") or "")[:200] for c in candidates
                ],
                "parse_ok": False,
                "parse_error": str(exc)[:200],
                "raw": raw[:2000],
                "kept": [],
            }
        )
        return []
    validator_debug(
        {
            "stage": "slm",
            "file_label": file_label,
            "candidates_in": [(c.get("description") or "")[:200] for c in candidates],
            "parse_ok": True,
            "raw": raw[:2000],
            "kept": kept,
            "enriched_code_chars": len(enriched_code),
        }
    )
    return kept
