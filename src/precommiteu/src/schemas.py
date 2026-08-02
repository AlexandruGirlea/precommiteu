from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FindingSource = Literal["precommiteu", "retrieval"]


class ModelFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(description="Short description of the likely issue.")


class ModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[ModelFinding]


class ValidatorFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_no: str
    code_evidence: str = Field(
        min_length=1,
        description="Exact visible code excerpt that proves the finding.",
    )
    description: str

    @field_validator("code_evidence")
    @classmethod
    def code_evidence_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code_evidence must not be blank")
        return value


class ValidatorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[ValidatorFinding]


class RegulationArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    article_number: int | str | None = None
    full_ref: str | None = None
    title: str | None = None
    external_celex: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regulation: str
    source: FindingSource
    file: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    probable_article_id: str | None = None
    code_evidence: str | None = None
    description: str
    eu_ignore_reason: str | None = None
    eu_ignore_source: Literal["inline", "config"] | None = None


class ScanStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regulation: str
    status: Literal["scanned", "skipped", "failed"]
    detail: str | None = None
    chunks_scanned: int = 0
    detector_candidates: int = 0
    validator_rejected: int = 0


class Advisory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regulation: str
    file: str
    description: str
    retrieval_verdict: str | None = None
    retrieval_confidence: float | None = None
    retrieval_similarity: float | None = None
    retrieval_article_id: str | None = None


class ScanResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]
    statuses: list[ScanStatus]
    advisories: list[Advisory] = []
