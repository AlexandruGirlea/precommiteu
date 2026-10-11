from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from precommiteu.regulations import adapter_checks


def finding(article):
    return {
        "article_no": article,
        "code_evidence": "store(record)",
        "description": "An allegation about backups must not influence the classifier.",
    }


def model_response(**fields):
    return Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps({
        "code_facts": "Observed source facts.", **fields,
    }))))


def check(article, model, *, regulation=None, deadline=None):
    return adapter_checks.check_findings(
        [finding(article)], "store(record)", model,
        regulation=regulation or article.split("_art")[0],
        file_label="not-a-classification-feature.py", deadline=deadline,
    )


@pytest.mark.parametrize(("article", "facts", "regulation"), [
    ("gdpr_art32", {"data": "public_nonpersonal"}, "gdpr"),
    ("eu_data_act_art25", {"service": "ordinary_business"}, "eu_data_act"),
    ("dora_art9", {"sector": "other", "operation": "runtime"}, "dora"),
    ("dora_art9", {"sector": "financial", "operation": "opaque_helper"}, "dora"),
    ("dsa_art27", {"operation": "recommendation_computation"}, "dsa"),
])
def test_explicit_source_context_can_reject_an_unsupported_allegation(article, facts, regulation):
    model = model_response(**facts)
    assert check(article, model, regulation=regulation) == []
    messages = model.invoke.call_args.args[0]
    assert "store(record)" in messages[1]["content"]
    assert finding(article)["description"] not in str(messages)
    assert "not-a-classification-feature.py" not in str(messages)
    assert "expected_articles" not in str(messages)


@pytest.mark.parametrize(("article", "facts", "expected"), [
    ("eu_data_act_art9", {"recipient": "product_user"}, "eu_data_act_art4"),
    ("dora_art9", {"sector": "financial", "operation": "backup"}, "dora_art12"),
])
def test_correction_preserves_evidence_and_replaces_the_stale_explanation(article, facts, expected):
    result = check(article, model_response(**facts))
    assert len(result) == 1
    assert result[0]["article_no"] == expected
    assert result[0]["code_evidence"] == finding(article)["code_evidence"]
    assert result[0]["description"].startswith("Observed source facts.")
    assert finding(article)["description"] not in result[0]["description"]


@pytest.mark.parametrize(("article", "regulation"), [
    ("gdpr_art32", "gdpr"), ("eu_data_act_art9", "eu_data_act"),
    ("eu_data_act_art25", "eu_data_act"),
    ("dora_art9", "dora"), ("dsa_art27", "dsa"),
])
def test_unknown_facts_preserve_the_original_finding(article, regulation):
    fields = adapter_checks._CHECKS[article][1]
    assert check(article, model_response(**dict.fromkeys(fields, "unknown")),
                 regulation=regulation) == [finding(article)]


@pytest.mark.parametrize(("regulation", "article"), [
    ("eu_ai_act", "eu_ai_act_art9"), ("eu_ai_act", "gdpr_art32"),
    ("gdpr", "dora_art9"), ("dora", "dora_art10"),
    ("cra_dma_nis2", "cra_art6"), ("cra_dma_nis2", "dma_art6"),
])
def test_unselected_articles_and_other_packs_never_call_the_classifier(regulation, article):
    model = Mock()
    assert check(article, model, regulation=regulation) == [finding(article)]
    model.invoke.assert_not_called()


@pytest.mark.parametrize("payload", [
    {}, {"code_facts": "Facts", "data": "invented_category"},
    {"code_facts": None, "data": "unknown"},
    {"code_facts": "Facts", "data": "unknown", "extra": True},
    {"code_facts": "Facts", "data": ["unknown"]},
])
def test_invalid_context_is_an_error_not_a_clean_result(payload):
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps(payload))))
    with pytest.raises(ValueError, match="invalid gdpr_art32 context classification"):
        check("gdpr_art32", model)


def test_all_checks_share_the_original_deadline(monkeypatch):
    monkeypatch.setattr(adapter_checks.time, "monotonic", Mock(side_effect=[103.0, 106.0]))
    model = model_response(data="unknown")
    rows = [finding("gdpr_art32"), finding("gdpr_art32")]
    assert adapter_checks.check_findings(
        rows, "store(record)", model, regulation="gdpr", file_label="test.py", deadline=110.0,
    ) == rows
    assert [call.kwargs["timeout_s"] for call in model.invoke.call_args_list] == [7.0, 4.0]


def test_expired_deadline_does_not_start_an_extra_call(monkeypatch):
    monkeypatch.setattr(adapter_checks.time, "monotonic", lambda: 110.0)
    model = Mock()
    with pytest.raises(TimeoutError):
        check("gdpr_art32", model, deadline=110.0)
    model.invoke.assert_not_called()


def test_context_grammar_excludes_literal_json_control_characters():
    grammar = adapter_checks._grammar({"data": ["unknown"]})
    assert r'char ::= [^"\\\x00-\x1f]' in grammar
    assert grammar.index("code_facts") < grammar.index("field-0")


def test_dora_runtime_findings_do_not_pay_for_a_backup_attribution_check():
    row = {**finding("dora_art9"), "description": "Strong authentication is disabled."}
    model = Mock()
    assert adapter_checks.check_findings(
        [row], "store(record)", model, regulation="dora", file_label="service.ts", deadline=None,
    ) == [row]
    model.invoke.assert_not_called()


def test_normal_validator_calls_the_context_check_and_preserves_other_findings():
    from precommiteu.regulations import get_regulation_pack
    from precommiteu.validator_call import call_validator

    original = [finding("gdpr_art32"), finding("gdpr_art6")]
    model = model_response(data="public_nonpersonal")
    model.invoke.side_effect = [
        SimpleNamespace(content=json.dumps({"findings": original})),
        model.invoke.return_value,
    ]
    result = call_validator(
        [{"description": "Initial allegation"}], "store(record)", "service.py", model,
        regulation_pack=get_regulation_pack("gdpr"), timeout_s=10.0,
    )
    assert result == [original[1]]
    assert model.invoke.call_count == 2
    assert 0 < model.invoke.call_args.kwargs["timeout_s"] <= 10.0
