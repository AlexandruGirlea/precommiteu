from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from precommiteu.regulations import RegulationPack
from precommiteu.validator_call import call_validator as _raw_call_validator

__all__ = ["CandidatesStore", "EnrichedCodeStore", "build_call_validator_tool"]


class EnrichedCodeStore:
    def __init__(self) -> None:
        self._by_label: dict[str, str] = {}

    def put(self, file_label: str, enriched_code: str) -> None:
        self._by_label[file_label] = enriched_code

    def get(self, file_label: str) -> str | None:
        return self._by_label.get(file_label)

    def labels(self) -> list[str]:
        return list(self._by_label.keys())


class CandidatesStore:
    def __init__(self) -> None:
        self._by_label: dict[str, list[dict]] = {}

    def put(self, file_label: str, candidates: list[dict]) -> None:
        self._by_label[file_label] = list(candidates)

    def get(self, file_label: str) -> list[dict]:
        return self._by_label.get(file_label, [])

    def labels(self) -> list[str]:
        return list(self._by_label.keys())


def build_call_validator_tool(
    *,
    validator_model: Any,
    enriched_code_store: EnrichedCodeStore,
    candidates_store: CandidatesStore,
    file_label_provider: Callable[[], str],
    kept_findings: list[dict[str, Any]],
    regulation_pack: RegulationPack,
    remaining_seconds: Callable[[], float] | None = None,
) -> Callable[..., str]:
    # Candidates come from the per-file detector cache, never from a tool arg:
    # the model cannot reliably escape nested JSON inside a string arg.
    def call_validator(article_id_hint: str = "") -> str:
        _ = article_id_hint
        file_label = file_label_provider()
        normalized = candidates_store.get(file_label)
        if not normalized:
            labels = candidates_store.labels()
            if labels:
                normalized = candidates_store.get(labels[-1])
        if not normalized:
            return json.dumps([])

        enriched_code = enriched_code_store.get(file_label)
        if enriched_code is None:
            labels = enriched_code_store.labels()
            if labels:
                enriched_code = enriched_code_store.get(labels[-1]) or ""
            else:
                enriched_code = ""

        kept = _raw_call_validator(
            candidates=normalized,
            enriched_code=enriched_code,
            file_label=file_label,
            model=validator_model,
            regulation_pack=regulation_pack,
            timeout_s=remaining_seconds() if remaining_seconds else None,
        )

        for vf in kept:
            decorated = dict(vf)
            decorated.setdefault("file", file_label)
            kept_findings.append(decorated)

        return json.dumps(kept)

    return call_validator
