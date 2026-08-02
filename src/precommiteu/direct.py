from __future__ import annotations

import logging
import time
from typing import Any

from precommiteu.agents.orchestrator import OrchestratorRun
from precommiteu.chunking import (
    USER_MESSAGE_TOKEN_BUDGET,
    CanonicalChunk,
    truncate_to_token_budget,
)
from precommiteu.config import CANDIDATE_FINDINGS_TOKEN_BUDGET
from precommiteu.detector_call import call_detector
from precommiteu.regulations import RegulationPack
from precommiteu.validator_call import call_validator

__all__ = ["run_direct"]

_LOG = logging.getLogger(__name__)

_VALIDATOR_VIEW_BUDGET = USER_MESSAGE_TOKEN_BUDGET - CANDIDATE_FINDINGS_TOKEN_BUDGET


def _as_added_diff(path_label: str, content: str) -> str:
    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    header = f"--- a/{path_label}\n+++ b/{path_label}\n@@ -0,0 +1,{len(lines)} @@\n"
    return header + "\n".join(f"+{line}" for line in lines)


def run_direct(
    *,
    chunks: list[CanonicalChunk],
    file_label: str,
    detector_model: Any,
    validator_model: Any,
    regulation_pack: RegulationPack,
    wall_seconds: float = 90.0,
) -> OrchestratorRun:
    run = OrchestratorRun(exit_reason="direct")
    deadline = time.monotonic() + wall_seconds
    for chunk in chunks:
        if time.monotonic() > deadline:
            if run.exit_reason == "direct":
                run.exit_reason = "budget_exhausted_time"
            break
        chunk_diff = _as_added_diff(file_label, chunk.text)
        run.consult_log.record(
            chunk.id, truncate_to_token_budget(chunk_diff, _VALIDATOR_VIEW_BUDGET)
        )
        try:
            candidates = call_detector(
                enriched_code=chunk_diff,
                model=detector_model,
                regulation_pack=regulation_pack,
                timeout_s=deadline - time.monotonic(),
            )
        except Exception as exc:
            _LOG.warning("direct: detector failed on %s %s: %r", file_label, chunk.id, exc)
            run.exit_reason = "direct_partial"
            continue
        run.detector_called = True
        run.tool_call_count += 1
        if not candidates:
            continue
        run.candidates_store.put(
            file_label, run.candidates_store.get(file_label) + candidates
        )
        try:
            kept = call_validator(
                candidates=candidates,
                enriched_code=chunk_diff,
                file_label=file_label,
                model=validator_model,
                regulation_pack=regulation_pack,
                timeout_s=deadline - time.monotonic(),
            )
        except Exception as exc:
            _LOG.warning("direct: validator failed on %s %s: %r", file_label, chunk.id, exc)
            run.exit_reason = "direct_partial"
            continue
        run.validator_called = True
        run.tool_call_count += 1
        for vf in kept:
            decorated = dict(vf)
            decorated.setdefault("file", file_label)
            decorated.setdefault("chunk_id", chunk.id)
            run.kept_findings.append(decorated)
    return run
