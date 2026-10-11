from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from precommiteu.grammar import validator_evidence_grammar
from precommiteu.regulations import get_regulation_pack
from precommiteu.regulations.eu_ai_act.validation_context import (
    FACTS_INSTRUCTIONS,
    facts_first_grammar,
    literal_fields_on_line,
)
from precommiteu.validator_call import call_validator


def validate(payload, regulation="eu_ai_act"):
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps(payload))))
    kept = call_validator(
        [{"description": "Check the operation."}], "monitor.start()", "service.py", model,
        regulation_pack=get_regulation_pack(regulation), timeout_s=5,
    )
    return kept, model


def test_facts_are_internal_and_source_options_are_unchanged():
    kept, model = validate({"code_facts": "The code starts monitoring.", "findings": []})
    assert kept == []
    model.invoke.assert_called_once()
    assert model.invoke.call_args.args[0][0]["content"].endswith(FACTS_INSTRUCTIONS)
    original = validator_evidence_grammar(["monitor.start()"])
    grammar = model.invoke.call_args.kwargs["grammar"]
    assert grammar != original
    assert grammar.index("code_facts") < grammar.index("findings")
    assert grammar == facts_first_grammar(original)
    assert grammar.split("evidence ::=", 1)[1] == original.split("evidence ::=", 1)[1]


@pytest.mark.parametrize("payload", [
    {"findings": []},
    {"code_facts": None, "findings": []},
    {"code_facts": {"actor": "provider"}, "findings": []},
    {"code_facts": "Source facts", "findings": [], "extra": "ignored?"},
    {"code_facts": "invented.disable()", "findings": [{
        "article_no": "eu_ai_act_art72", "code_evidence": "invented.disable()",
        "description": "An observation is not source evidence.",
    }]},
])
def test_invalid_facts_or_citing_facts_as_code_fails_validation(payload):
    with pytest.raises(ValueError, match="invalid findings or source evidence"):
        validate(payload)


@pytest.mark.parametrize("regulation", ["gdpr", "eu_data_act", "dora", "dsa"])
def test_other_packs_use_the_original_grammar_and_schema(regulation):
    kept, model = validate({"findings": []}, regulation)
    assert kept == []
    expected = validator_evidence_grammar(["monitor.start()"])
    assert model.invoke.call_args.kwargs["grammar"] == expected
    assert FACTS_INSTRUCTIONS not in model.invoke.call_args.args[0][0]["content"]
    with pytest.raises(ValueError):
        validate({"code_facts": "Unsupported for this pack.", "findings": []}, regulation)


def test_combined_pack_uses_measured_facts_first_schema():
    kept, model = validate({"code_facts": "Observed source facts.", "findings": []}, "cra_dma_nis2")
    assert kept == []
    assert model.invoke.call_args.kwargs["grammar"] == facts_first_grammar(
        validator_evidence_grammar(["monitor.start()"])
    )
    with pytest.raises(ValueError):
        validate({"findings": []}, "cra_dma_nis2")


def test_literal_facts_are_confined_to_the_evidence_line():
    code = 'other.configure(enabled=False)\nmark.configure(ui_visible=False, machine_readable=True)'
    evidence = code.splitlines()[1]
    assert literal_fields_on_line(code, evidence) == {"ui_visible": False, "machine_readable": True}
    assert literal_fields_on_line(code, "invented.enable()") == {}


def test_literal_dictionary_values_and_assignments_without_resolving_variables():
    code = ('def metadata():\n'
            '    visible = False\n'
            '    return {"ui": visible,\n'
            '            "notified_body_involved": False, "notified_body_id": None}\n')
    assert literal_fields_on_line(code, "visible = False") == {"visible": False}
    assert literal_fields_on_line(code, 'return {"ui": visible,') == {}
    assert literal_fields_on_line(code, code.splitlines()[3]) == {
        "notified_body_involved": False, "notified_body_id": None,
    }


def test_unsupported_syntax_calls_and_conflicting_literals_are_not_evaluated():
    code = 'dangerous.configure(enabled=execute_arbitrary_code())'
    assert literal_fields_on_line(code, code) == {}
    code = 'f(enabled=True); g(enabled=False)'
    assert literal_fields_on_line(code, code) == {}
    assert literal_fields_on_line('const enabled = true;', 'const enabled = true;') == {}
