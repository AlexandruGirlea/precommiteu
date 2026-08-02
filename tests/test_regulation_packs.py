from __future__ import annotations

import re

import pytest

from precommiteu.regulations import get_regulation_pack
from precommiteu.src.regulations import SUPPORTED_REGULATIONS, normalize_regulation

PACKAGED = ("gdpr", "eu_ai_act", "eu_data_act", "dora", "dsa", "cra_dma_nis2")


@pytest.mark.parametrize("name", PACKAGED)
def test_every_packaged_regulation_loads(name):
    pack = get_regulation_pack(name)

    assert pack.name == name
    assert pack.detector_system.strip()
    assert pack.validator_system.strip()
    assert pack.regulations_summary.strip()


@pytest.mark.parametrize("name", PACKAGED)
def test_sample_article_id_is_well_formed(name):
    # cra_dma_nis2 is a combined pack, so its articles carry sub-regulation
    # prefixes (cra_art4) rather than the pack name.
    assert re.fullmatch(r"[a-z][a-z0-9_]*_art\d+", get_regulation_pack(name).sample_article_id)


def test_missing_regulation_pack_raises():
    with pytest.raises(ModuleNotFoundError):
        get_regulation_pack("not_a_regulation")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("gdpr", "gdpr"),
        ("GDPR", "gdpr"),
        ("eu_ai_act", "eu-ai-act"),
        ("ai-act", "eu-ai-act"),
        ("  data_act  ", "eu-data-act"),
    ],
)
def test_normalize_regulation_resolves_aliases_and_case(value, expected):
    assert normalize_regulation(value) == expected
    assert expected in SUPPORTED_REGULATIONS


def test_normalize_regulation_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown regulation"):
        normalize_regulation("hipaa")
