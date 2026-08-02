from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

__all__ = [
    "DEFAULT_REGULATION",
    "REGULATIONS_ROOT",
    "RegulationPack",
    "get_regulation_pack",
    "get_sample_article_id",
]

REGULATIONS_ROOT = "precommiteu.regulations"
DEFAULT_REGULATION = "gdpr"

_ARTICLE_HEADING_RE = re.compile(
    r"^\s*#{1,6}\s+([a-z][a-z0-9]*_art\d+)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _scan_first_article_id(regulations_summary: str) -> str | None:
    match = _ARTICLE_HEADING_RE.search(regulations_summary)
    if match is None:
        return None
    return match.group(1).lower()


@cache
def pack_article_ids(name: str) -> frozenset[str]:
    try:
        pkg = files(f"{REGULATIONS_ROOT}.{name}")
        text = (pkg / "regulations_summary.md").read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError, OSError):
        return frozenset()
    return frozenset(
        re.findall(rf"^##\s+({re.escape(name)}_art\d+)\s*$", text, re.MULTILINE)
    )


def get_sample_article_id(name: str) -> str:
    pkg = files(f"{REGULATIONS_ROOT}.{name}")
    metadata_path = pkg.joinpath("metadata.json")
    if metadata_path.is_file():
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        sample = data.get("sample_article_id")
        if isinstance(sample, str) and sample.strip():
            return sample.strip()
    summary_path = pkg.joinpath("regulations_summary.md")
    if summary_path.is_file():
        try:
            summary = summary_path.read_text(encoding="utf-8")
        except OSError:
            summary = ""
        scanned = _scan_first_article_id(summary)
        if scanned is not None:
            return scanned
    return f"{name}_art1"


@dataclass(frozen=True)
class RegulationPack:
    name: str
    detector_system: str
    validator_system: str
    regulations_summary: str
    sample_article_id: str


@cache
def get_regulation_pack(name: str) -> RegulationPack:
    pkg = files(f"{REGULATIONS_ROOT}.{name}")
    return RegulationPack(
        name=name,
        detector_system=pkg.joinpath("detector_summary.md").read_text(encoding="utf-8"),
        validator_system=pkg.joinpath("validator_summary.md").read_text(encoding="utf-8"),
        regulations_summary=pkg.joinpath("regulations_summary.md").read_text(encoding="utf-8"),
        sample_article_id=get_sample_article_id(name),
    )
