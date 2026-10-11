"""Check scope and article assignments using facts from the source.

The model classifies the code without seeing the initial allegation. The rules
below keep, correct or discard the finding. Unknown facts keep the finding.
"""
from __future__ import annotations

import json
import time

from precommiteu.debuglog import validator_debug
from precommiteu.grammar import VALIDATOR_GBNF
from precommiteu.src.scanner import _normalize_validator_article_id

# Legal basis for the checks below.
# https://eur-lex.europa.eu/eli/reg/2016/679/oj (Articles 2, 4, 32)
# https://eur-lex.europa.eu/eli/reg/2023/2854/oj (Articles 4, 9, 23, 25)
# https://eur-lex.europa.eu/eli/reg/2022/2554/oj (Articles 2, 9, 12)
# https://eur-lex.europa.eu/eli/reg/2022/2065/oj (Articles 27, 38)
_CHECKS = {
    "gdpr_art32": (
        "Describe the data and purpose of the cited operation. Choose personal_data "
        "for identified/identifiable people's data, credentials for authentication secrets, "
        "public_nonpersonal for public artifacts or nonpersonal measurements, or unknown. "
        "The choice depends on the actual input and purpose, not on which algorithm or "
        "protocol is used. Do not invent personal data inside unspecified inputs.",
        {"data": ["personal_data", "credentials", "public_nonpersonal", "unknown"]},
    ),
    "eu_data_act_art9": (
        "Identify who pays for whose data. Choose product_user for a user's request to "
        "access their own connected-product data; business_recipient for a holder's "
        "compensation charged to a third-party data recipient; unknown otherwise. "
        "Do not choose the category from the existence or size of a charge.",
        {"recipient": ["product_user", "business_recipient", "unknown"]},
    ),
    "eu_data_act_art25": (
        "Describe the actual service whose contract or exit is configured. Choose "
        "data_processing_service for cloud, edge or comparable data-processing services; "
        "ordinary_business for an unrelated physical service or ordinary business "
        "subscription; unknown when unclear. A notice period alone does not identify "
        "the service. Do not evaluate the period's legality.",
        {"service": ["data_processing_service", "ordinary_business", "unknown"]},
    ),
    "dora_art9": (
        "Describe the actor and cited operation without judging compliance. sector is "
        "financial for a financial entity's ICT operations, other for an established "
        "nonfinancial activity, unknown otherwise. operation is backup for storing or "
        "restoring financial backups; runtime for a visible runtime security setting; "
        "opaque_helper for a call whose implementation and security settings are not "
        "shown; unknown otherwise. Do not invent weaknesses inside an opaque helper.",
        {"sector": ["financial", "other", "unknown"],
         "operation": ["backup", "runtime", "opaque_helper", "unknown"]},
    ),
    "dsa_art27": (
        "Describe the operation actually shown. Choose transparency_setting for "
        "disclosure of recommender parameters, choice_setting for configuring a user's "
        "choice among ranking options, recommendation_computation for computing/ranking "
        "recommendations without showing the disclosure or choice interface, or unknown. "
        "Do not infer absent interface features from a computation helper.",
        {"operation": ["transparency_setting", "choice_setting",
                       "recommendation_computation", "unknown"]},
    ),
}

_PACK_PREFIXES = {
    "gdpr": ("gdpr_",), "eu_data_act": ("eu_data_act_",), "dora": ("dora_",),
    "dsa": ("dsa_",),
}

_CORRECTIONS = {
    "eu_data_act_art4": "Article 4 requires holder-mediated access to the user's own "
    "connected-product data to be free of charge to that user.",
    "dora_art12": "Article 12 requires appropriate protection for financial-entity "
    "backups and restoration procedures.",

}


def _decision(article: str, facts: dict) -> str | None:
    if article == "gdpr_art32" and facts["data"] == "public_nonpersonal":
        return None
    if article == "eu_data_act_art9" and facts["recipient"] == "product_user":
        return "eu_data_act_art4"
    if article == "eu_data_act_art25" and facts["service"] == "ordinary_business":
        return None
    if article == "dora_art9" and facts["sector"] == "other":
        return None
    if article == "dora_art9":
        if facts["operation"] == "opaque_helper":
            return None
        if facts["operation"] == "backup":
            return "dora_art12"
    if article == "dsa_art27" and facts["operation"] == "recommendation_computation":
        return None
    return article


def _grammar(fields: dict[str, list[str]]) -> str:
    properties = [json.dumps('"code_facts"') + ' ":" string']
    properties += [json.dumps(json.dumps(key)) + f' ":" field-{i}'
                   for i, key in enumerate(fields)]
    grammar = 'root ::= "{" ' + ' "," '.join(properties) + ' "}"\n'
    grammar += "\n".join(
        f"field-{i} ::= " + " | ".join(json.dumps(json.dumps(value)) for value in values)
        for i, values in enumerate(fields.values())
    )
    strings = VALIDATOR_GBNF[VALIDATOR_GBNF.index("string ::="):]
    # JSON forbids literal newlines and other control characters in strings.
    strings = strings.replace(r'char ::= [^"\\]', r'char ::= [^"\\\x00-\x1f]')
    return grammar + "\n" + strings


def check_findings(findings, code, model, *, regulation, file_label, deadline):
    kept = []
    for finding in findings:
        article = _normalize_validator_article_id(finding["article_no"], regulation)
        if (regulation not in _PACK_PREFIXES or article not in _CHECKS
            or not article.startswith(_PACK_PREFIXES[regulation])):
            kept.append(finding)
            continue
        # Recheck backup findings for Article 12; other Article 9 findings need no extra call.
        if article == "dora_art9" and "backup" not in (
            finding["description"] + " " + finding["code_evidence"]
        ).casefold():
            kept.append(finding)
            continue
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            raise TimeoutError("adapter context check exhausted the validator budget")
        prompt, fields = _CHECKS[article]
        prompt += ("\nFirst give code_facts describing the visible source without a legal "
                   "conclusion. Then return the category fields: " + ", ".join(fields) + ".")
        user = f"<code>\n{code}\n</code>\n"
        if article not in {"eu_data_act_art9", "eu_data_act_art25"}:
            user += f'<cited_operation>\n{finding["code_evidence"]}\n</cited_operation>'
        response = model.invoke(
            [{"role": "system", "content": prompt},
             {"role": "user", "content": user}],
            grammar=_grammar(fields), timeout_s=remaining,
        )
        facts = json.loads(response.content)
        if (not isinstance(facts, dict) or set(facts) != {"code_facts", *fields}
            or not isinstance(facts["code_facts"], str)
            or any(facts[key] not in values for key, values in fields.items())):
            raise ValueError(f"invalid {article} context classification")
        decision = _decision(article, facts)
        validator_debug({"stage": "adapter_context", "file_label": file_label,
                         "regulation": regulation, "article_no": article,
                         "facts": facts, "checked_article_no": decision,
                         "code_evidence": finding["code_evidence"]})
        if decision is None:
            continue
        if decision != article:
            kept.append({**finding, "article_no": decision,
                         "description": facts["code_facts"] + " " + _CORRECTIONS[decision]})
        else:
            kept.append(finding)
    return kept
