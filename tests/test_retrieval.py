from __future__ import annotations

from precommiteu.chunking import token_chunks
from precommiteu.scan import _apply_retrieval, _load_case_index
from precommiteu.src.schemas import Advisory


def test_crm_case_match_remains_an_advisory(risky_code):
    path = risky_code / "CrmSyncJob.java"
    code = path.read_text(encoding="utf-8")
    # Detector allegation from the reported false positive; no model call needed.
    advisory = Advisory(
        regulation="eu_ai_act",
        file=path.name,
        description=(
            "The code exports special categories of personal data (national ID, home address, "
            "date of birth) to a third-party CRM API without pseudonymization or any other "
            "privacy-preserving measures. This violates the strict safeguards required when "
            "processing such sensitive data for purposes unrelated to its original collection."
        ),
    )
    index = _load_case_index("eu_ai_act")
    assert index is not None

    findings, advisories = _apply_retrieval(
        case_index=index,
        file_advisories=[advisory],
        code=code,
        regulation="eu_ai_act",
        chunks=token_chunks(path, code),
        inline_markers=[],
    )

    assert findings == []
    assert len(advisories) == 1
    assert advisories[0].description == advisory.description
    assert advisories[0].retrieval_article_id == "eu_ai_act_art71"
    assert advisories[0].retrieval_verdict == "violation_pattern"
