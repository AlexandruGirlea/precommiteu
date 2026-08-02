from __future__ import annotations

import contextlib
import json
from functools import lru_cache
from importlib.resources import files
from typing import Final

from precommiteu.src.schemas import RegulationArticle

SUPPORTED_REGULATIONS: Final[tuple[str, ...]] = (
    "cra",
    "cra-dma-nis2",
    "dma",
    "dora",
    "dsa",
    "eu-ai-act",
    "eu-data-act",
    "gdpr",
    "nis2",
)

ALIASES: Final[dict[str, str]] = {
    "aia": "eu-ai-act",
    "ai-act": "eu-ai-act",
    "ai_act": "eu-ai-act",
    "eu_ai_act": "eu-ai-act",
    "data-act": "eu-data-act",
    "data_act": "eu-data-act",
    "eu_data_act": "eu-data-act",
    "cyber-resilience-act": "cra",
    "digital-markets-act": "dma",
    "digital-services-act": "dsa",
}

_EURLEX_REGULATION_URL = (
    "https://eur-lex.europa.eu/LexUriServ/LexUriServ.do?uri=CELEX:{celex}:EN:HTML"
)

def normalize_regulation(value: str) -> str:
    key = value.strip().lower().replace("_", "-")
    key = ALIASES.get(key, key)
    if key not in SUPPORTED_REGULATIONS:
        supported = supported_regulations_help()
        raise ValueError(f"Unknown regulation '{value}'. Supported: {supported}")
    return key


@lru_cache(maxsize=1)
def regulation_index() -> dict[str, dict]:
    path = files("precommiteu.src").joinpath("regulations.json")
    return json.loads(path.read_text(encoding="utf-8"))


def article_for(regulation: str, article_id: str | None) -> RegulationArticle | None:
    if not article_id:
        return None
    reg = normalize_regulation(regulation)
    if "_art" in article_id:
        prefix = article_id.rsplit("_art", 1)[0].replace("_", "-")
        with contextlib.suppress(ValueError):
            reg = normalize_regulation(prefix)
    for raw in regulation_index().get(reg, {}).get("articles", []):
        if raw.get("id") == article_id:
            return RegulationArticle.model_validate(raw)
    return None


def regulation_display_name(regulation: str) -> str:
    try:
        reg = normalize_regulation(regulation)
    except ValueError:
        return regulation
    info = regulation_index().get(reg, {})
    return info.get("name") or reg.upper()


def regulation_full_name(regulation: str) -> str:
    try:
        reg = normalize_regulation(regulation)
    except ValueError:
        return regulation
    info = regulation_index().get(reg, {})
    return info.get("full_name") or regulation_display_name(reg)


def regulation_label(regulation: str) -> str:
    try:
        reg = normalize_regulation(regulation)
    except ValueError:
        return regulation
    short = regulation_display_name(reg)
    full = regulation_full_name(reg)
    suffix = f" ({short})"
    if full.endswith(suffix):
        full = full[: -len(suffix)]
    if short.lower() == full.lower():
        return short
    return f"{short} ({full})"


def supported_regulations_help() -> str:
    return ", ".join(regulation_label(reg) for reg in SUPPORTED_REGULATIONS)


def article_url(article_id: str | None) -> str | None:
    if not article_id:
        return None

    if "_art" not in article_id:
        return None
    reg_prefix, art_part = article_id.rsplit("_art", 1)
    if not art_part or not art_part[0].isdigit():
        return None
    with contextlib.suppress(ValueError):
        reg_key = normalize_regulation(reg_prefix)
        celex = regulation_index().get(reg_key, {}).get("celex")
        if celex is not None:
            return _EURLEX_REGULATION_URL.format(celex=celex)
    if reg_prefix == "ai":
        celex = regulation_index().get("eu-ai-act", {}).get("celex")
        if celex is not None:
            return _EURLEX_REGULATION_URL.format(celex=celex)
        return None
    return None


def article_display_label(article_id: str | None) -> str | None:
    if not article_id or "_art" not in article_id:
        return None
    reg_prefix, art_part = article_id.rsplit("_art", 1)
    if not art_part or not art_part[0].isdigit():
        return None
    reg_key = reg_prefix.lower().replace("_", "-")
    if reg_key == "ai":
        reg_key = "eu-ai-act"
    try:
        reg_key = normalize_regulation(reg_key)
        reg_display = regulation_display_name(reg_key)
    except ValueError:
        reg_display = reg_prefix.upper().replace("_", " ")

    parts = art_part.split("_")
    art_num = parts[0]
    extras = "".join(f"({p})" for p in parts[1:] if p)
    return f"{reg_display} Art. {art_num}{extras}"
