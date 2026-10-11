"""Recheck selected AI Act findings against the source.

Each check receives the code without the initial allegation. It can remove a
finding or correct its article, while preserving the quoted evidence.
"""
from __future__ import annotations

import json
import re
import time

from precommiteu.debuglog import validator_debug
from precommiteu.grammar import VALIDATOR_GBNF
from precommiteu.regulations.eu_ai_act.validation_context import literal_fields_on_line
from precommiteu.src.scanner import _normalize_validator_article_id

_CHECKS = {
    "eu_ai_act_art5": """Is a prohibited AI operation actually executed?
Examples: biometric emotion inference on staff or students (except medical/safety
purposes), sensitive-trait biometric categorisation, untargeted face scraping for
a recognition database, social-behaviour scores denying unrelated services, or
crime prediction solely from profiling. Unused model parameters, descriptive
names, self-reported moods and one-to-one authentication do not perform these
operations. Building a facial-recognition database through untargeted scraping
also qualifies before model inference.""",
    "eu_ai_act_art12": """Does the cited operation disable required automatic event
logging of a high-risk AI system? For remote biometric identification only,
missing use start/end, reference database, matched input or verifier identity
also qualify. Those biometric-specific fields are not mandatory for ordinary
credit scoring logs. A recorded decision need not include raw credit inputs.""",
    "eu_ai_act_art14": """Does the code disable or bypass effective human oversight
of a high-risk AI system? Pure one-to-one identity verification for login is not
high-risk remote biometric identification. An active review queue is a safeguard;
a disabled review queue is not. Do not infer missing oversight from an isolated
model call when no high-risk use or explicit bypass is shown.""",
    "eu_ai_act_art19": """Read the actual retention value and units for controlled
automatic logs of high-risk AI. One month is below six months; six months meets
the minimum, as do longer periods. Generic business logs are outside this duty.
Return eu_ai_act_art19 for provider logs below six months, eu_ai_act_art26 for
deployer logs below six months, or none if the floor is met or no breach is shown.
A bank operating a credit AI is a deployer, even if a candidate said provider.""",
    "eu_ai_act_art47": """Does the code actually omit or disable the high-risk AI
declaration or its required identification/signature? Evaluate the branch value:
True followed by if True executes signing. Both physical and electronic
signatures are allowed. A call that signs the declaration is a safeguard, not a
defect. Do not presume fields inside a declaration-building helper are missing.""",
    "eu_ai_act_art55": """First establish that the GPAI model has SYSTEMIC RISK.
General-purpose status alone is insufficient. A designation or the training
compute presumption above 10^25 FLOP can establish that status; 10^18 FLOP with
no designation cannot. Then check whether adversarial evaluation, systemic-risk
mitigation, serious-incident reporting or model security is actually disabled.""",
    "eu_ai_act_art78": """This duty concerns information obtained while carrying
out AI Act regulatory tasks, such as a market surveillance investigation.
Does the cited operation expose that confidential information? public_read=True
exposes it; public_read=False does not. Do not infer missing encryption or access
control inside a storage helper whose implementation is not supplied.
Ordinary support logs and customer exports are outside this article.""",
}
# Article 26 covers many deployer duties beyond retention. Only recheck findings
# initially assigned to the log-specific Article 19; they may be reassigned to 26.
_LOG_ARTICLES = {"eu_ai_act_art19": "provider", "eu_ai_act_art26": "deployer"}


def check_findings(
    findings: list[dict], code: str, model, *, file_label: str, deadline: float | None
) -> list[dict]:
    kept = []
    for finding in findings:
        article = _normalize_validator_article_id(finding["article_no"], "eu_ai_act")
        if article not in _CHECKS:
            kept.append(finding)
            continue
        allowed = [*_LOG_ARTICLES, "none"] if article in _LOG_ARTICLES else [article, "none"]
        instruction = (
            '\nReturn JSON with article_no set to the applicable article from '
            + ', '.join(allowed[:-1]) + ' if the cited operation in context demonstrates '
            'that defect, or {"article_no":"none"} otherwise.'
            if article in _LOG_ARTICLES else
            '\nReturn only {"article_no":"' + article +
            '"} if the cited operation in context demonstrates that defect, '
            'or {"article_no":"none"} otherwise.'
        )
        grammar = (
            'root ::= "{\\\"article_no\\\":\\\"" article "\\\"}"\narticle ::= '
            + " | ".join(json.dumps(a) for a in allowed)
        )
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            raise TimeoutError("AI Act article check exhausted the validator budget")
        response = model.invoke(
            [
                {"role": "system", "content": _CHECKS[article] + instruction},
                {"role": "user", "content": f"<code>\n{code}\n</code>\n"
                 f'<cited_operation>\n{finding["code_evidence"]}\n</cited_operation>'},
            ],
            timeout_s=remaining, grammar=grammar,
        )
        checked = json.loads(response.content).get("article_no")
        if checked not in allowed:
            raise ValueError(f"invalid {article} article check result")
        validator_debug({
            "stage": "article_check", "file_label": file_label,
            "article_no": article, "checked_article_no": checked,
            "code_evidence": finding["code_evidence"],
        })
        if checked == "none":
            continue
        if checked != article:
            # Only the two automatic-log duties can be reassigned by this check.
            kept.append({
                **finding, "article_no": checked,
                "description": f"The quoted retention setting deletes {_LOG_ARTICLES[checked]}-"
                "controlled high-risk AI logs before the six-month minimum required by "
                f"Article {checked.removeprefix('eu_ai_act_art')}.",
            })
        else:
            kept.append(finding)
    return _refine_context(kept, code, model, file_label=file_label, deadline=deadline)


# Deployer duties under Article 26(2),
# (4), (5), (7): https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-26
_ATTRIBUTION = {
    "eu_ai_act_art14": """Identify the duty shown in the cited code operation.
Return eu_ai_act_art26 if an operator/deployer fails to assign trained, competent
human oversight personnel to a high-risk AI system it uses.
Return eu_ai_act_art14 for provider design of override/stop/review capabilities,
or if the specific deployer personnel duty is not established.""",
    "eu_ai_act_art73": """Identify who is responsible for the incident notification.
A provider reports serious incidents under eu_ai_act_art73. A deployer using the
system must immediately notify its provider and competent authority under
eu_ai_act_art26. Keep eu_ai_act_art73 if this is a provider's reporting mechanism,
or a deployer explicitly taking over reporting because the provider is unreachable.
Do not infer that an argument named provider makes the enclosing operator a provider.""",
}
_DEPLOYER_DESCRIPTIONS = {
    "eu_ai_act_art10": "The quoted operation disables relevance and representativeness checks "
    "for deployer-controlled operational input data to high-risk AI. "
    "Article 26 requires the deployer to ensure suitable input data.",
    "eu_ai_act_art14": "The quoted operation disables assignment of competent human oversight "
    "personnel for a deployed high-risk AI system. Article 26 requires "
    "the deployer to assign trained people with authority to oversee it.",
    "eu_ai_act_art73": "The quoted operation disables serious-incident notifications by the "
    "deployer to the provider and competent authority. Article 26 requires "
    "these notifications immediately after a serious incident is identified.",
    "eu_ai_act_art86": "The quoted operation disables notification of affected workers and their "
    "representatives before workplace use of high-risk AI. Article 26 "
    "requires the employer to provide that notice before using the system.",
}

# The model extracts facts; _context_decision applies the article rules.
_CONTEXT = {
    "eu_ai_act_art10": ("""Describe how the code uses data, not its legal compliance.
Choose training_data for AI training, validation or test datasets and their governance.
Choose operational_inputs for a deployer's checks of the relevance/representativeness
of inputs to a high-risk AI system it operates. Choose ordinary_processing for records,
forms or business preferences with no demonstrated AI training or inference activity.
Sensitive data alone does not establish AI activity. Choose other if unclear.
The category does not depend on whether safeguards are enabled or disabled.""",
        {"activity": ["training_data", "operational_inputs", "ordinary_processing", "other"]}),
    "eu_ai_act_art53": ("""Describe the business activity implemented by the code.
Choose gpai_training for a pipeline feeding a general-purpose or foundation model's
training corpus. Choose ordinary_crawling for fetching pages for a search index or
website cache without model training. Choose other when neither is established.
This category does not depend on whether copyright checks are enabled or disabled.
Do not evaluate legal compliance.""",
        {"activity": ["gpai_training", "ordinary_crawling", "other"]}),
    "eu_ai_act_art86": ("""Describe the purpose of the code, irrespective of whether
its controls are enabled or disabled. Choose worker_notice for an employer's notice
to workers and their representatives about workplace AI use. Choose decision_explanation
for providing or refusing an explanation of an individual AI-assisted credit, hiring,
benefit or similar decision. Choose ordinary_processing for simple records, self-reported
survey responses or other processing with no AI inference or AI decision context.
Choose other if the purpose is unclear. A helper need not execute inference itself
to handle an explanation of an existing AI decision. Do not evaluate compliance.""",
        {"activity": ["worker_notice", "decision_explanation", "ordinary_processing", "other"]}),
    "eu_ai_act_art48": ("""Extract concrete CE configuration fields from the code.
focus: body if the cited line contains notified-body participation or identification
fields, including fields of a returned dictionary; mark if it contains CE visibility
or machine-readable configuration; other otherwise.
body: involved if a notified body participates, not_involved if participation is
explicitly false or assessment is internal, unknown otherwise.
ui and machine_readable: enabled for a true/1 flag, disabled for a false/0 flag,
unknown when that configuration is not shown. These describe configuration values,
not whether the whole application is legally compliant or accessible.
Do not infer missing configuration from a helper whose body is not supplied.""",
        {"focus": ["body", "mark", "other"],
         "body": ["involved", "not_involved", "unknown"],
         "ui": ["enabled", "disabled", "unknown"],
         "machine_readable": ["enabled", "disabled", "unknown"]}),
    "eu_ai_act_art60": ("""Read the real-world AI trial code without evaluating compliance.
operation: stop_testing if the cited line stops a subject's participation; erasure if
it configures deletion/retention of subject data; other for duration, transfers,
decision reversal or other testing operations.
erasure_request: present if the code handles an express request to erase personal
data (including a function explicitly handling withdrawal AND an erasure request);
not_shown for withdrawal alone with no erasure request; unknown if ambiguous.
stopped: yes if the subject's testing is stopped, no if it explicitly continues,
unknown if not shown. Do not infer an erasure request from withdrawal alone.""",
        {"operation": ["stop_testing", "erasure", "other"],
         "erasure_request": ["present", "not_shown", "unknown"],
         "stopped": ["yes", "no", "unknown"]}),
    "eu_ai_act_art46": ("""Read the actual values and branches in this emergency AI
authorisation-refusal handler. operation is discard_outputs only when the cited
operation configures deletion/discarding of outputs; otherwise other.
discard is enabled if output deletion actually executes (for example a True flag
tested by an if branch), disabled if bypassed, or unknown if not shown.
Do not evaluate compliance or infer the value from the flag's name.""",
        {"operation": ["discard_outputs", "other"], "discard": ["enabled", "disabled", "unknown"]}),
}


def _context_decision(article: str, facts: dict) -> str:
    """Apply scope and exception rules to the extracted facts."""
    if article == "eu_ai_act_art10":
        return {"operational_inputs": "eu_ai_act_art26", "ordinary_processing": "none"}.get(
            facts["activity"], article,
        )
    if article == "eu_ai_act_art53" and facts["activity"] == "ordinary_crawling":
        return "none"
    if article == "eu_ai_act_art86":
        return {"worker_notice": "eu_ai_act_art26", "ordinary_processing": "none"}.get(
            facts["activity"], article,
        )
    # Article 48(2), (4): interface OR electronic access; body number where applicable.
    if article == "eu_ai_act_art48":
        if facts["focus"] == "mark" and "enabled" in (facts["ui"], facts["machine_readable"]):
            return "none"
        if (facts["focus"] == "body" and facts["body"] == "not_involved"
            and (facts["ui"], facts["machine_readable"]) != ("disabled", "disabled")):
            return "none"
    # Article 60(5): stopping participation alone does not establish an erasure request.
    if article == "eu_ai_act_art60" and (
        facts["stopped"] == "yes" and (
            (facts["operation"] == "stop_testing" and facts["erasure_request"] != "present")
            or (facts["operation"] == "erasure" and facts["erasure_request"] == "not_shown")
        )
    ):
        return "none"
    if article == "eu_ai_act_art46" and (
        facts["operation"] == "discard_outputs" and facts["discard"] == "enabled"
    ):
        return "none"
    return article


def _ground_ce_fields(facts: dict, code: str, evidence: str) -> dict:
    """Use literal CE settings from the evidence line when the model disagrees."""
    aliases = {}
    for key, value in literal_fields_on_line(code, evidence).items():
        normalized = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
        aliases.setdefault(normalized, []).append(value)
    fields = {key: values[0] for key, values in aliases.items()
              if all(type(value) is type(values[0]) and value == values[0] for value in values)}
    grounded = dict(facts)
    mark = bool(fields.keys() & {"ui_visible", "machine_readable"})
    body = bool(fields.keys() & {"notified_body_involved", "notified_body_id"})
    if mark != body:
        grounded["focus"] = "mark" if mark else "body"
    for source, target in (("ui_visible", "ui"), ("machine_readable", "machine_readable")):
        value = fields.get(source)
        if type(value) in (bool, int) and value in (0, 1):
            grounded[target] = "enabled" if value else "disabled"
    value = fields.get("notified_body_involved")
    if type(value) in (bool, int) and value in (0, 1):
        grounded["body"] = "involved" if value else "not_involved"
    return grounded


def _context_grammar(fields: dict[str, list[str]]) -> str:
    grammar = 'root ::= "{" ' + json.dumps('"code_facts"') + ' ":" string "," '
    grammar += ' "," '.join(
        json.dumps(json.dumps(key)) + f' ":" field-{index}'
        for index, key in enumerate(fields)
    ) + ' "}"\n'
    # GBNF rule names do not allow underscores. JSON property names are separate
    # literals; numbered rules also avoid collisions with string/char productions.
    grammar += "\n".join(
        f"field-{index} ::= " + " | ".join(json.dumps(json.dumps(v)) for v in values)
        for index, values in enumerate(fields.values())
    )
    return grammar + "\n" + VALIDATOR_GBNF[VALIDATOR_GBNF.index("string ::="):]


def _refine_context(findings, code, model, *, file_label, deadline):
    kept = []
    for finding in findings:
        article = _normalize_validator_article_id(finding["article_no"], "eu_ai_act")
        if article not in _ATTRIBUTION and article not in _CONTEXT:
            kept.append(finding)
            continue
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            raise TimeoutError("AI Act context check exhausted the validator budget")
        user = f"<code>\n{code}\n</code>\n"
        # Activity is a property of the whole snippet, not a single flag assignment.
        if article not in ("eu_ai_act_art10", "eu_ai_act_art53", "eu_ai_act_art86"):
            user += f'<cited_operation>\n{finding["code_evidence"]}\n</cited_operation>'
        if article in _CONTEXT:
            prompt, fields = _CONTEXT[article]
            prompt += (
                "\nFirst give code_facts: a short description of the actual fields or activity "
                "in the code, without a legal conclusion. Then give these category fields: "
                + ", ".join(fields) + "."
            )
            grammar = _context_grammar(fields)
        else:
            allowed = [article, "eu_ai_act_art26"]
            prompt = (_ATTRIBUTION[article] + "\nReturn only JSON with article_no "
                      "set to one of: " + ", ".join(allowed) + ".")
            grammar = ('root ::= "{\\\"article_no\\\":\\\"" article "\\\"}"\narticle ::= '
                       + " | ".join(json.dumps(a) for a in allowed))
        response = model.invoke(
            [{"role": "system", "content": prompt}, {"role": "user", "content": user}],
            timeout_s=remaining, grammar=grammar,
        )
        facts = json.loads(response.content)
        if not isinstance(facts, dict):
            raise ValueError(f"invalid {article} context result")
        model_facts = facts
        if article in _CONTEXT:
            if (set(facts) != {"code_facts", *fields}
                or not isinstance(facts["code_facts"], str)
                or any(facts[key] not in values for key, values in fields.items())):
                raise ValueError(f"invalid {article} context classification")
            if article == "eu_ai_act_art48":
                facts = _ground_ce_fields(facts, code, finding["code_evidence"])
            if (article == "eu_ai_act_art60" and facts["operation"] == "stop_testing"
                and literal_fields_on_line(code, finding["code_evidence"])):
                # A quoted literal setting alone cannot establish that a subject's
                # testing was stopped. Do not grant the withdrawal exception on it.
                facts = {**facts, "operation": "other"}
            decision = _context_decision(article, facts)
        else:
            if set(facts) != {"article_no"} or facts["article_no"] not in allowed:
                raise ValueError(f"invalid {article} attribution")
            decision = facts["article_no"]
        event = {
            "stage": "article_context", "file_label": file_label, "article_no": article,
            "facts": facts, "checked_article_no": decision,
            "code_evidence": finding["code_evidence"],
        }
        if facts != model_facts:
            event["model_facts"] = model_facts
        validator_debug(event)
        if decision == "none":
            continue
        if decision != article:
            kept.append({**finding, "article_no": decision,
                         "description": _DEPLOYER_DESCRIPTIONS[article]})
        else:
            kept.append(finding)
    return kept
