from __future__ import annotations

import io
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from precommiteu import model_factory, validator_call
from precommiteu.direct import _as_added_diff, run_direct
from precommiteu.regulations import get_regulation_pack
from precommiteu.scan import _translate_kept_findings
from precommiteu.src.chunk_view import CanonicalChunk, ChunkConsultLog


def _model(evidence):
    payload = {
        "findings": [
            {
                "article_no": "eu_ai_act_art5",
                "code_evidence": evidence,
                "description": "Workplace emotion recognition from employee webcam frames.",
            }
        ]
    }
    return Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps(payload))))


def _validate(code, model):
    return validator_call.call_validator(
        candidates=[{"description": "Workplace emotion recognition."}],
        enriched_code=code,
        file_label="CrmSyncJob.java",
        model=model,
        regulation_pack=get_regulation_pack("eu_ai_act"),
    )


def test_line_selection_copies_exact_code_and_preserves_source_locations():
    code = (
        "void sync() {\n"
        "    employeeEmotion = model.infer(employeeWebcamFrame);\n"
        '    record.put("employee_emotion", employeeEmotion);\n'
        "}\n"
    )
    diff = _as_added_diff("CrmSyncJob.java", code)
    expected = "employeeEmotion = model.infer(employeeWebcamFrame);"
    model = _model(expected)

    kept = _validate(diff, model)

    assert kept[0]["code_evidence"] == expected
    messages = model.invoke.call_args.args[0]
    assert "+    employeeEmotion = model.infer(employeeWebcamFrame);" in messages[1]["content"]
    grammar = model.invoke.call_args.kwargs["grammar"]
    assert json.dumps(json.dumps(expected)) in grammar
    chunk = CanonicalChunk("part", "CrmSyncJob.java", 40, 43, code)
    consulted = ChunkConsultLog()
    consulted.record(chunk.id, diff)
    findings, rejected = _translate_kept_findings(
        regulation="eu_ai_act",
        file_label="CrmSyncJob.java",
        chunks=[chunk],
        consult_log=consulted,
        kept_findings=kept,
        inline_markers=[],
    )

    assert rejected == 0
    assert len(findings) == 1
    assert findings[0].probable_article_id == "eu_ai_act_art5"
    assert findings[0].code_evidence == expected.strip()
    assert (findings[0].start_line, findings[0].end_line) == (41, 41)


@pytest.mark.parametrize(
    "evidence",
    [
        "employee_emotion = client.send(...).body()",
        "client.send(...).body();",
        "client.send(request)",
        "// client.send(request).body();",
        "",
    ],
)
def test_fabricated_or_partial_evidence_fails_instead_of_becoming_a_finding(evidence):
    with pytest.raises(ValueError, match="invalid findings or source evidence"):
        _validate("client.send(request).body();", _model(evidence))


@pytest.mark.parametrize(
    "evidence",
    [
        "--- a/job.java",
        "+++ b/job.java",
        "@@ -1 +1 @@",
        "model.infer(employeeWebcamFrame);",
    ],
)
def test_diff_headers_and_deleted_code_cannot_be_evidence(evidence):
    diff = (
        "--- a/job.java\n+++ b/job.java\n@@ -1 +1 @@\n"
        "-model.infer(employeeWebcamFrame);\n+showConsent();\n"
    )
    model = _model(evidence)
    with pytest.raises(ValueError, match="invalid findings or source evidence"):
        _validate(diff, model)
    grammar = model.invoke.call_args.kwargs["grammar"]
    assert "model.infer" not in grammar


def test_line_selection_cannot_cite_code_hidden_by_the_token_budget(monkeypatch):
    monkeypatch.setattr(validator_call, "USER_MESSAGE_TOKEN_BUDGET", 600)
    model = _model("hidden();")
    with pytest.raises(ValueError, match="invalid findings or source evidence"):
        _validate("visible();\n" + "x" * 1000 + "\nhidden();", model)
    prompt = model.invoke.call_args.args[0][1]["content"]
    assert "visible();" in prompt
    assert "[...TRUNCATED...]" in prompt
    assert "hidden();" not in prompt


def test_validator_can_reject_candidates_without_selecting_evidence():
    model = Mock(invoke=Mock(return_value=SimpleNamespace(content='{"findings":[]}')))
    assert _validate("exportContacts();", model) == []


def test_comments_only_do_not_supply_evidence():
    model = Mock()
    assert _validate("// model.infer(employeeWebcamFrame);", model) == []
    model.invoke.assert_not_called()


def test_invalid_evidence_marks_the_scan_incomplete():
    detector = Mock(
        invoke=Mock(
            return_value=SimpleNamespace(
                content=(
                    '<findings>{"findings":[{"description":'
                    '"Workplace emotion recognition."}]}</findings>'
                )
            )
        )
    )
    run = run_direct(
        chunks=[CanonicalChunk("part", "CrmSyncJob.java", 1, 1, "client.send(request).body();")],
        file_label="CrmSyncJob.java",
        detector_model=detector,
        validator_model=_model("client.send(...).body();"),
        regulation_pack=get_regulation_pack("eu_ai_act"),
    )
    assert run.exit_reason == "direct_partial"
    assert run.detector_called
    assert not run.validator_called
    assert run.kept_findings == []


def test_model_uses_source_grammar_only_for_the_current_request(monkeypatch):
    requests = []

    def open_response(request, **kwargs):
        requests.append(json.loads(request.data))
        return io.BytesIO(b'{"choices":[{"message":{"content":"ok"}}]}')

    monkeypatch.setattr(model_factory.LOOPBACK_OPENER, "open", open_response)
    model = model_factory.LocalChatModel(
        endpoint="http://127.0.0.1:1/chat/completions",
        api_key="test",
        temperature=0,
        max_tokens=100,
        grammar="default",
        timeout_s=1,
        retries=0,
    )
    model.invoke([], grammar="source-one")
    model.invoke([], grammar="source-two")
    model.invoke([])

    assert [request["grammar"] for request in requests] == ["source-one", "source-two", "default"]
