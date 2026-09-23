from __future__ import annotations

import json
import logging
import os
import sys
import time

from precommiteu.chunking import (
    APPROX_TOKENS,
    USER_MESSAGE_TOKEN_BUDGET,
    truncate_to_token_budget,
)
from precommiteu.config import CANDIDATE_FINDINGS_TOKEN_BUDGET
from precommiteu.debuglog import validator_debug
from precommiteu.grammar import validator_evidence_grammar
from precommiteu.regulations import RegulationPack
from precommiteu.src.scanner import (
    _current_code_from_chunk,
    _normalize_validator_article_id,
    _validator_evidence_specific_enough,
)
from precommiteu.src.schemas import ValidatorOutput

logger = logging.getLogger(__name__)

_DEBUG_ENRICH = bool(os.environ.get("PRECOMMITEU_DEBUG_ENRICH"))
_RAW_PREVIEW_CHARS = 400

_ARTICLE78_ACTIVITY = (
    "Describe the business activity implemented by the code. "
    "Do not evaluate its security or legal compliance.\n"
    "Choose ai_act_duties if it obtains or processes information for AI Act market surveillance, "
    "a regulatory investigation, or conformity assessment.\n"
    "Choose ordinary_activity for customer records, support tickets, routine business logging, "
    "or an AI product's normal operation.\n"
    "The activity category is the same whether file permissions are secure or insecure.\n"
    'Return JSON: {"activity":"ai_act_duties"} or {"activity":"ordinary_activity"}.'
)
_ARTICLE59_ACTIVITY = (
    "Describe the business activity implemented by the code. "
    "Do not evaluate its security or legal compliance.\n"
    "Choose ai_act_duties if it processes personal data for developing, training or testing "
    "AI systems in an AI regulatory sandbox, including deletion when participation ends.\n"
    "Choose ordinary_activity for customer records, CRM exports, routine business logging, "
    "or a generic software development/test sandbox without an AI regulatory sandbox context.\n"
    "The activity category is the same whether data protections are present or missing.\n"
    'Return JSON: {"activity":"ai_act_duties"} or {"activity":"ordinary_activity"}.'
)
_AI_ACT_ACTIVITY_CHECKS = {
    "eu_ai_act_art78": _ARTICLE78_ACTIVITY,
    "eu_ai_act_art59": _ARTICLE59_ACTIVITY,
}
_AI_ACT_ACTIVITY_GRAMMAR = (
    r'root ::= "{\"activity\":\"ai_act_duties\"}" | "{\"activity\":\"ordinary_activity\"}"'
)

_EVIDENCE_INSTRUCTIONS = """
For code_evidence, choose ONE complete visible code line that most directly shows
the defect. Copy it exactly, omitting only leading/trailing whitespace and the
diff '+' or context-space prefix. Never rename variables or abbreviate with '...'.
The output grammar restricts this field to actual source lines. Use surrounding
code to judge applicability and explain the defect in description as usual.
"""


def _source_evidence_options(text: str) -> list[str]:
    lines = text.splitlines()
    if lines and lines[-1] == "[...TRUNCATED...]":
        # The preceding line may have been cut mid-statement; never cite it.
        lines = lines[:-2]
    current_code = _current_code_from_chunk("\n".join(lines))
    return list(
        dict.fromkeys(
            line.strip()
            for line in current_code.splitlines()
            if _validator_evidence_specific_enough(line.strip())
            and not line.lstrip().startswith(("#", "//", "/*", "*", "<!--"))
        )
    )


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
    evidence_options = _source_evidence_options(enriched_code)
    if not evidence_options:
        return []

    candidates_json = json.dumps(
        {
            "candidates": [
                {"description": (c.get("description") or "").strip()} for c in candidates
            ],
        },
        ensure_ascii=False,
    )
    user_message = (
        f"<code_or_diff>\n{enriched_code}\n</code_or_diff>\n\n"
        f"<candidate_findings>\n{candidates_json}\n</candidate_findings>"
    )

    messages = [
        {"role": "system", "content": pack.validator_system + "\n" + _EVIDENCE_INSTRUCTIONS},
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

    started = time.monotonic()
    response = model.invoke(
        messages, timeout_s=timeout_s, grammar=validator_evidence_grammar(evidence_options)
    )
    raw = getattr(response, "content", "") or ""

    try:
        parsed = ValidatorOutput.model_validate_json(raw)
        kept = []
        for finding in parsed.findings:
            if finding.code_evidence not in evidence_options:
                raise ValueError("validator evidence is not an allowed source line")
            kept.append(
                {
                    "article_no": finding.article_no,
                    "code_evidence": finding.code_evidence,
                    "description": finding.description,
                }
            )
        checks = _AI_ACT_ACTIVITY_CHECKS if pack.name == "eu_ai_act" else {}
        for article_no, activity_prompt in checks.items():
            scoped = [
                f
                for f in kept
                if _normalize_validator_article_id(f["article_no"], pack.name) == article_no
            ]
            if not scoped:
                continue
            remaining = None if timeout_s is None else timeout_s - (time.monotonic() - started)
            if remaining is not None and remaining <= 0:
                raise TimeoutError(f"{article_no} activity check exhausted the validator budget")
            # Classify the activity independently of the detector's alleged violation.
            activity_response = model.invoke(
                [
                    {"role": "system", "content": activity_prompt},
                    {
                        "role": "user",
                        "content": f"<code>\n{_current_code_from_chunk(enriched_code)}\n</code>",
                    },
                ],
                timeout_s=remaining,
                grammar=_AI_ACT_ACTIVITY_GRAMMAR,
            )
            activity = json.loads(activity_response.content).get("activity")
            if activity not in ("ai_act_duties", "ordinary_activity"):
                raise ValueError(f"invalid {article_no} activity classification")
            validator_debug(
                {
                    "stage": "article_activity", "file_label": file_label,
                    "article_no": article_no, "activity": activity,
                }
            )
            if activity == "ordinary_activity":
                kept = [f for f in kept if f not in scoped]
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
                "candidates_in": [(c.get("description") or "")[:200] for c in candidates],
                "parse_ok": False,
                "parse_error": str(exc)[:200],
                "raw": raw[:2000],
                "kept": [],
            }
        )
        raise ValueError("validator returned invalid findings or source evidence") from exc
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
