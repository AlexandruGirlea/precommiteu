from __future__ import annotations

import pathlib

import pytest

from precommiteu.src.schemas import Finding

RISKY_CODE = pathlib.Path(__file__).parent / "fixtures" / "risky_code"


@pytest.fixture
def risky_code() -> pathlib.Path:
    return RISKY_CODE


def make_finding(**overrides) -> Finding:
    fields = {
        "regulation": "gdpr",
        "source": "precommiteu",
        "file": "user_store.py",
        "start_line": 10,
        "end_line": 12,
        "probable_article_id": "gdpr_art32",
        "code_evidence": "sqlite3.connect(self.path)",
        "description": "Personal data stored without encryption at rest.",
    }
    fields.update(overrides)
    return Finding(**fields)
