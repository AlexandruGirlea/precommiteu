from __future__ import annotations

import html
from typing import Any

from precommiteu.src.regulations import (
    article_display_label,
    article_for,
    article_url,
    regulation_display_name,
)
from precommiteu.src.schemas import Finding

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
TOOL_NAME = "precommiteu"

# HTML-escape all attacker-controllable text fields; the GitHub Code Scanning
# renderer is not guaranteed to sanitize SARIF.


def _rule_id(finding: Finding) -> str:
    if finding.probable_article_id:
        return finding.probable_article_id
    return f"{finding.regulation}:unknown"


def _rule_name(finding: Finding) -> str:
    label = article_display_label(finding.probable_article_id)
    if label:
        return label
    return regulation_display_name(finding.regulation)


def _article_title(finding: Finding) -> str | None:
    try:
        article = article_for(finding.regulation, finding.probable_article_id)
    except ValueError:
        return None
    return article.title if article else None


def _has_cited_article(finding: Finding) -> bool:
    if not finding.probable_article_id:
        return False
    try:
        return article_for(finding.regulation, finding.probable_article_id) is not None
    except ValueError:
        return False


def _build_rules_index(findings: list[Finding]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for f in findings:
        rid = _rule_id(f)
        if rid in seen:
            continue
        title = _article_title(f)
        rule: dict[str, Any] = {
            "id": rid,
            "name": _rule_name(f),
            "shortDescription": {
                "text": html.escape(title or _rule_name(f)),
            },
            "fullDescription": {
                "text": html.escape(
                    f"Compliance check for {regulation_display_name(f.regulation)}. "
                    f"Auto-detected by Precommiteu's regulation-aware SLM. "
                    "Always review before treating as a hard violation."
                ),
            },
        }
        url = article_url(f.probable_article_id)
        if url:
            rule["helpUri"] = url
        seen[rid] = rule
    return list(seen.values())


def _build_result(finding: Finding) -> dict[str, Any]:
    region: dict[str, Any] = {}
    if finding.start_line is not None:
        region["startLine"] = max(1, int(finding.start_line))
    if finding.end_line is not None:
        region["endLine"] = max(region.get("startLine", 1), int(finding.end_line))

    location: dict[str, Any] = {
        "physicalLocation": {
            "artifactLocation": {
                "uri": finding.file or "<unknown>",
                "uriBaseId": "%SRCROOT%",
            },
        }
    }
    if region:
        location["physicalLocation"]["region"] = region

    properties: dict[str, Any] = {
        "source": finding.source,
        "regulation": finding.regulation,
    }
    if finding.probable_article_id:
        properties["probable_article_id"] = finding.probable_article_id
    if finding.code_evidence:
        properties["code_evidence"] = finding.code_evidence
    if finding.eu_ignore_reason:
        properties["eu_ignored"] = True
        properties["eu_ignore_reason"] = finding.eu_ignore_reason
        if finding.eu_ignore_source:
            properties["eu_ignore_source"] = finding.eu_ignore_source

    return {
        "ruleId": _rule_id(finding),
        "message": {"text": html.escape(finding.description or "")},
        "locations": [location],
        "properties": properties,
    }


def findings_to_sarif(findings: list[Finding]) -> dict[str, Any]:
    cited_findings = [f for f in findings if _has_cited_article(f)]
    rules = _build_rules_index(cited_findings)
    results = [_build_result(f) for f in cited_findings]
    return {
        "version": SARIF_VERSION,
        "$schema": SARIF_SCHEMA_URI,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "rules": rules,
                    },
                },
                "results": results,
            },
        ],
    }
