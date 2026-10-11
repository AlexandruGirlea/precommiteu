from __future__ import annotations

import json
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from precommiteu import validator_call
from precommiteu.regulations import get_regulation_pack
from precommiteu.regulations.eu_ai_act import article_checks


def _finding(article="eu_ai_act_art5", evidence="model.predict(face)"):
    return {"article_no": article, "code_evidence": evidence,
            "description": "An allegation that must not bias the independent check."}


def _model(*decisions):
    return Mock(invoke=Mock(side_effect=[
        SimpleNamespace(content=json.dumps({"article_no": decision})) for decision in decisions
    ]))


def _check(findings, model, *, code="model.predict(face)", deadline=None):
    return article_checks.check_findings(
        findings, code, model, file_label="example.py", deadline=deadline,
    )


def test_rejection_preserves_unrelated_findings_and_exact_evidence():
    rejected = _finding()
    confirmed = _finding("Article 14", "review.disabled = True")
    unrelated = _finding("eu_ai_act_art72", "monitor.collect = False")
    model = _model("none", "eu_ai_act_art14", "eu_ai_act_art14")

    assert _check([rejected, confirmed, unrelated], model) == [confirmed, unrelated]
    assert model.invoke.call_count == 3
    messages = model.invoke.call_args_list[0].args[0]
    assert messages[1]["content"] == (
        "<code>\nmodel.predict(face)\n</code>\n"
        "<cited_operation>\nmodel.predict(face)\n</cited_operation>"
    )
    assert rejected["description"] not in str(messages)


@pytest.mark.parametrize("original,corrected,actor,number", [
    ("Article 19", "eu_ai_act_art26", "deployer", "26"),
])
def test_log_attribution_corrects_actor_and_description_without_changing_evidence(
    original, corrected, actor, number
):
    finding = _finding(original, "logs.set_retention(months=1)")
    kept = _check([finding], _model(corrected))

    assert kept[0]["article_no"] == corrected
    assert kept[0]["code_evidence"] == finding["code_evidence"]
    assert f"{actor}-controlled" in kept[0]["description"]
    assert f"Article {number}." in kept[0]["description"]
    assert finding["article_no"] == original  # Do not mutate the caller's findings.


@pytest.mark.parametrize("response", [
    "not JSON", "{}", '{"article_no":"eu_ai_act_art48"}', '{"article_no":null}',
])
def test_malformed_or_out_of_scope_decision_is_an_error(response):
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content=response)))
    with pytest.raises(ValueError):
        _check([_finding()], model)


def test_one_deadline_covers_all_article_checks(monkeypatch):
    ticks = iter([103.0, 107.0, 111.0])
    monkeypatch.setattr(article_checks.time, "monotonic", lambda: next(ticks))
    model = _model("eu_ai_act_art5", "eu_ai_act_art5")

    with pytest.raises(TimeoutError):
        _check([_finding(), _finding(), _finding()], model, deadline=110.0)
    assert [call.kwargs["timeout_s"] for call in model.invoke.call_args_list] == [7.0, 3.0]


@pytest.mark.parametrize("article", ["eu_ai_act_art72", "eu_ai_act_art26", "Article 26"])
def test_empty_or_unhandled_findings_do_not_invoke_the_model(article):
    model = Mock()
    finding = _finding(article)
    assert _check([], model) == []
    assert _check([finding], model) == [finding]
    model.invoke.assert_not_called()


@pytest.mark.parametrize("regulation", ["gdpr", "eu_data_act", "dora", "dsa", "cra_dma_nis2"])
@pytest.mark.parametrize("number", [5, 10, 12, 14, 19, 26, 46, 47, 48, 53, 55, 73, 78, 86])
def test_ai_article_checks_do_not_run_for_other_regulations(regulation, number):
    finding = _finding(f"Article {number}")
    payload = {"findings": [finding]}
    if regulation == "cra_dma_nis2":
        payload["code_facts"] = "Observed source facts."
    model = Mock(invoke=Mock(return_value=SimpleNamespace(
        content=json.dumps(payload),
    )))
    pack = get_regulation_pack(regulation)

    kept = validator_call.call_validator(
        [{"description": "Original candidate"}], finding["code_evidence"], "example.py", model,
        regulation_pack=pack, timeout_s=9.0,
    )

    assert kept == [finding]
    model.invoke.assert_called_once()
    assert model.invoke.call_args.kwargs["timeout_s"] == 9.0
    assert model.invoke.call_args.args[0][0]["content"] == (
        pack.validator_system + "\n" + validator_call._EVIDENCE_INSTRUCTIONS
        + (validator_call.FACTS_INSTRUCTIONS if regulation == "cra_dma_nis2" else "")
    )


def test_validator_uses_current_diff_code_and_shares_its_original_budget(monkeypatch):
    ticks = iter([100.0, 103.0])
    monkeypatch.setattr(validator_call.time, "monotonic", lambda: next(ticks))
    finding = _finding()
    model = Mock(invoke=Mock(side_effect=[
        SimpleNamespace(content=json.dumps({
            "code_facts": "Observed operation", "findings": [finding],
        })),
        SimpleNamespace(content='{"article_no":"none"}'),
    ]))

    assert validator_call.call_validator(
        [{"description": "Original candidate"}],
        "--- a/example.py\n+++ b/example.py\n@@ -1 +1 @@\n-old_code()\n+model.predict(face)",
        "example.py", model, regulation_pack=get_regulation_pack("eu_ai_act"), timeout_s=10.0,
    ) == []
    check_call = model.invoke.call_args_list[1]
    assert check_call.kwargs["timeout_s"] == 7.0
    assert "old_code" not in check_call.args[0][1]["content"]
    assert "Original candidate" not in str(check_call.args)


def test_article_check_failure_propagates_instead_of_returning_a_clean_scan():
    finding = _finding()
    model = Mock(invoke=Mock(side_effect=[
        SimpleNamespace(content=json.dumps({
            "code_facts": "Observed operation", "findings": [finding],
        })),
        TimeoutError("model timed out"),
    ]))
    with pytest.raises(ValueError) as error:
        validator_call.call_validator(
            [{"description": "Original candidate"}], finding["code_evidence"], "example.py",
            model, regulation_pack=get_regulation_pack("eu_ai_act"),
        )
    assert isinstance(error.value.__cause__, TimeoutError)


@pytest.mark.parametrize("original", [10, 14, 73, 86])
def test_only_specific_deployer_duties_are_reassigned_and_evidence_is_preserved(original):
    article = f"eu_ai_act_art{original}"
    finding = _finding(article, "gate.enabled = False")
    responses = []
    if original == 14:
        responses.append({"article_no": article})
    responses.append(
        {"code_facts": "Observed purpose", "activity": (
            "worker_notice" if original == 86 else "operational_inputs"
        )} if original in (10, 86) else {"article_no": "eu_ai_act_art26"}
    )
    model = Mock(invoke=Mock(side_effect=[
        SimpleNamespace(content=json.dumps(response)) for response in responses
    ]))
    kept = _check([finding], model)
    assert kept[0]["article_no"] == "eu_ai_act_art26"
    assert kept[0]["code_evidence"] == finding["code_evidence"]
    assert "Article 26" in kept[0]["description"]
    assert finding["article_no"] == article
    assert finding["description"] not in str(model.invoke.call_args_list)


@pytest.mark.parametrize("focus,body,ui,machine,retained", [
    ("body", "not_involved", "unknown", "enabled", False),
    ("body", "involved", "unknown", "enabled", True),
    ("body", "unknown", "unknown", "enabled", True),
    ("body", "not_involved", "disabled", "disabled", True),
    ("mark", "unknown", "disabled", "enabled", False),
    ("mark", "unknown", "enabled", "disabled", False),
    ("mark", "not_involved", "disabled", "disabled", True),
    ("other", "not_involved", "unknown", "enabled", True),
])
def test_ce_exception_does_not_excuse_an_inaccessible_mark_or_another_defect(
    focus, body, ui, machine, retained,
):
    finding = _finding("eu_ai_act_art48", "mark.configure(settings)")
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps(
        {"code_facts": "Fields observed in source", "focus": focus, "body": body,
         "ui": ui, "machine_readable": machine},
    ))))
    assert _check([finding], model) == ([finding] if retained else [])


@pytest.mark.parametrize("article,facts", [
    ("eu_ai_act_art10", {"activity": "other"}),
    ("eu_ai_act_art10", {"activity": "training_data"}),
    ("eu_ai_act_art53", {"activity": "other"}),
    ("eu_ai_act_art86", {"activity": "other"}),
    ("eu_ai_act_art86", {"activity": "decision_explanation"}),
    ("eu_ai_act_art46", {"operation": "discard_outputs", "discard": "unknown"}),
])
def test_uncertain_context_preserves_the_finding(article, facts):
    finding = _finding(article)
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps(
        {"code_facts": "Incomplete source context", **facts},
    ))))
    assert _check([finding], model) == [finding]


@pytest.mark.parametrize("payload", [
    [], {"activity": "ordinary_processing"},
    {"code_facts": None, "activity": "ordinary_processing"},
    {"code_facts": "Records", "activity": "not_an_allowed_category"},
    {"code_facts": "Records", "activity": "ordinary_processing", "extra": "invalid"},
])
def test_invalid_context_is_an_error_not_a_clean_result(payload):
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps(payload))))
    with pytest.raises(ValueError):
        _check([_finding("eu_ai_act_art86")], model)


def test_context_check_uses_the_existing_deadline(monkeypatch):
    ticks = iter([106.0, 111.0])
    monkeypatch.setattr(article_checks.time, "monotonic", lambda: next(ticks))
    model = _model("eu_ai_act_art73")
    with pytest.raises(TimeoutError):
        _check([_finding("eu_ai_act_art73"), _finding("eu_ai_act_art73")], model, deadline=110.0)
    model.invoke.assert_called_once()
    assert model.invoke.call_args.kwargs["timeout_s"] == 4.0


@pytest.mark.parametrize("operation,erasure_request,stopped,retained", [
    ("stop_testing", "not_shown", "yes", False),
    ("stop_testing", "unknown", "yes", False),
    ("erasure", "present", "yes", True),
    ("erasure", "unknown", "yes", True),
    ("stop_testing", "not_shown", "no", True),
    ("other", "not_shown", "yes", True),
])
def test_withdrawal_exception_preserves_erasure_requests_and_other_trial_duties(
    operation, erasure_request, stopped, retained,
):
    finding = _finding("eu_ai_act_art60")
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps({
        "code_facts": "Observed withdrawal operations", "operation": operation,
        "erasure_request": erasure_request, "stopped": stopped,
    }))))
    assert _check([finding], model) == ([finding] if retained else [])


def test_all_context_grammars_use_valid_unique_gbnf_rule_names():
    fields_to_check = [fields for _, fields in article_checks._CONTEXT.values()]
    # JSON property spelling must not become an invalid or colliding GBNF rule.
    fields_to_check.append({"machine_readable": ["yes", "no"], "string": ["unknown"]})
    for fields in fields_to_check:
        grammar = article_checks._context_grammar(fields)
        names = [line.split(" ::= ", 1)[0] for line in grammar.splitlines() if " ::= " in line]
        assert len(names) == len(set(names))
        assert all(re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*", name) for name in names)
        for key, values in fields.items():
            assert json.dumps(json.dumps(key)) in grammar
            assert all(json.dumps(json.dumps(value)) in grammar for value in values)


def test_literal_ce_fields_override_contradictory_model_classification():
    facts = {"code_facts": "A mark configuration", "focus": "body", "body": "involved",
             "ui": "disabled", "machine_readable": "disabled"}
    evidence = "mark.configure(ui_visible=False, machine_readable=True)"
    grounded = article_checks._ground_ce_fields(facts, evidence, evidence)
    assert grounded["focus"] == "mark"
    assert grounded["machine_readable"] == "enabled"
    assert article_checks._context_decision("eu_ai_act_art48", grounded) == "none"
    assert facts["machine_readable"] == "disabled"


def test_literal_body_participation_preserves_a_real_missing_number():
    facts = {"code_facts": "Metadata", "focus": "other", "body": "not_involved",
             "ui": "unknown", "machine_readable": "enabled"}
    evidence = 'return {"notifiedBodyInvolved": True, "notifiedBodyId": None}'
    grounded = article_checks._ground_ce_fields(facts, 'def mark():\n    '+evidence, evidence)
    assert grounded["focus"] == "body"
    assert grounded["body"] == "involved"
    assert article_checks._context_decision("eu_ai_act_art48", grounded) == "eu_ai_act_art48"


def test_conflicting_aliases_cannot_override_context():
    facts = {"code_facts": "Ambiguous configuration", "focus": "other", "body": "unknown",
             "ui": "unknown", "machine_readable": "unknown"}
    code = "mark.configure(machine_readable=True, machineReadable=False)"
    assert article_checks._ground_ce_fields(facts, code, code) == facts


def test_withdrawal_exception_cannot_remove_a_cited_disabled_setting():
    code = "trial.stop_testing(subject)\nerase = False"
    finding = _finding("eu_ai_act_art60", "erase = False")
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps({
        "code_facts": "A stopped trial and disabled deletion setting",
        "operation": "stop_testing", "erasure_request": "unknown", "stopped": "yes",
    }))))
    assert _check([finding], model, code=code) == [finding]
