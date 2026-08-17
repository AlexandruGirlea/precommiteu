from __future__ import annotations

import json
import os
import pathlib
import re

from precommiteu.ui import install

DEMO_CATALOG = pathlib.Path(
    os.environ.get("PRECOMMITEU_UI_CATALOG")
    or pathlib.Path.cwd() / "demo_ui" / "catalog.json"
)
PACK_FIELDS = ("jurisdiction", "id", "name", "reference", "covers", "timeline")
ADAPTER_MB = 77

JURISDICTIONS = [
    {
        "id": "eu",
        "flag": "🇪🇺",
        "name": "European Union",
        "blurb": "Six detector packs covering eight regulations, all local.",
        "live": True,
    },
]

PACKS = [
    ("eu", "eu_ai_act", "EU AI Act", "Regulation (EU) 2024/1689",
     "Systems that build, serve or call AI models; automated decisions, biometrics.",
     "Applies 2 Aug 2026 (prohibitions since Feb 2025)"),
    ("eu", "gdpr", "GDPR", "Regulation (EU) 2016/679",
     "Personal data: collection, retention, consent, subject rights, security.",
     "In force since 25 May 2018"),
    ("eu", "dora", "DORA", "Regulation (EU) 2022/2554",
     "ICT risk, resilience testing and incident reporting for financial entities.",
     "Applies since 17 Jan 2025"),
    ("eu", "dsa", "Digital Services Act", "Regulation (EU) 2022/2065",
     "Content moderation, notice-and-action, recommender transparency, minors.",
     "Applies since 17 Feb 2024"),
    ("eu", "eu_data_act", "Data Act", "Regulation (EU) 2023/2854",
     "Access to connected-product data, switching, cloud portability.",
     "Applies since 12 Sep 2025"),
    ("eu", "cra_dma_nis2", "CRA · DMA · NIS2",
     "(EU) 2024/2847 · (EU) 2022/1925 · Directive (EU) 2022/2555",
     "Product cybersecurity, gatekeeper duties, network and information security.",
     "CRA from 11 Dec 2027 · NIS2 since Oct 2024"),
]


def _demo_overlay() -> tuple[list[dict], list[tuple]]:
    try:
        data = json.loads(DEMO_CATALOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], []
    packs = [
        tuple(pack[field] for field in PACK_FIELDS)
        for pack in data.get("packs", [])
        if all(field in pack for field in PACK_FIELDS)
    ]
    return data.get("jurisdictions", []), packs


def _article_titles(pack_id: str) -> dict[str, str]:
    # Keyed by the full article id: a multi-regulation pack has a cra_art6 and a
    # dma_art6, and the bare number loses one of them.
    try:
        from importlib.resources import files
        text = (files(f"precommiteu.regulations.{pack_id}")
                / "regulations_summary.md").read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError, OSError):
        return {}
    return {
        article_id.lower(): title.strip()
        for article_id, title in re.findall(
            r"^##\s+(\w+_art\d+)\s*$.*?^Title:\s*(.+?)$",
            text,
            re.MULTILINE | re.DOTALL,
        )
    }


def build(models_dir: pathlib.Path) -> dict:
    demo_jurisdictions, demo_packs = _demo_overlay()
    # The shared base is fetched with whichever pack is downloaded first. The
    # adapter is 1.7% of the download, so it lands long before the base: without
    # the base a pack with an adapter on disk is not usable yet.
    have_base = install.base_ok(models_dir)
    base_mb = 0 if have_base else install.BASE_MB
    packs = []
    for jurisdiction, pid, name, ref, covers, timeline in PACKS + demo_packs:
        adapter = models_dir / pid / install.ADAPTER
        installed = have_base and adapter.is_file()
        titles = _article_titles(pid)
        packs.append(
            {
                "jurisdiction": jurisdiction,
                "id": pid,
                "name": name,
                "reference": ref,
                "covers": covers,
                "timeline": timeline,
                "articles": len(titles),
                "titles": titles if installed else {},
                "installed": installed,
                "path": str(adapter) if installed else None,
                "size_mb": round(adapter.stat().st_size / 1048576) if installed
                else ADAPTER_MB,
                "download_mb": ADAPTER_MB + base_mb,
                "status": "installed" if installed else (
                    "available" if jurisdiction == "eu" else "unavailable"
                ),
            }
        )
    counts: dict[str, int] = {}
    for pack in packs:
        if pack["installed"]:
            counts[pack["jurisdiction"]] = counts.get(pack["jurisdiction"], 0) + 1
    jurisdictions = [
        {**j, "installed": counts.get(j["id"], 0),
         "total": sum(1 for p in packs if p["jurisdiction"] == j["id"])}
        for j in JURISDICTIONS + demo_jurisdictions
    ]
    return {"jurisdictions": jurisdictions, "packs": packs}
