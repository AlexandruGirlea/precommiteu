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


def _model(evidence, article_no="eu_ai_act_art5"):
    payload = {
        "findings": [
            {
                "article_no": article_no,
                "code_evidence": evidence,
                "description": "Workplace emotion recognition from employee webcam frames.",
            }
        ]
    }
    return Mock(invoke=Mock(return_value=SimpleNamespace(content=json.dumps(payload))))


def _validate(code, model, **kwargs):
    return validator_call.call_validator(
        candidates=[{"description": "Workplace emotion recognition."}],
        enriched_code=code,
        file_label="CrmSyncJob.java",
        model=model,
        regulation_pack=get_regulation_pack("eu_ai_act"),
        **kwargs,
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
    assert model.invoke.call_count == 1


@pytest.mark.parametrize(
    "article_no", ["eu_ai_act_art78", "Article 78", "eu_ai_act_art59", "Article 59"]
)
@pytest.mark.parametrize(
    "activity,expected_count", [("ordinary_activity", 0), ("ai_act_duties", 1)]
)
def test_scoped_article_requires_independently_established_activity(
    article_no, activity, expected_count
):
    code = "Files.setPosixFilePermissions(logFile, WORLD_READABLE);"
    model = _model(code, article_no)
    model.invoke.side_effect = [
        model.invoke.return_value,
        SimpleNamespace(content=json.dumps({"activity": activity})),
    ]

    assert len(_validate(_as_added_diff("audit.java", code), model)) == expected_count
    scope_messages = model.invoke.call_args.args[0]
    assert scope_messages[1]["content"] == f"<code>\n{code}\n</code>"
    assert "Workplace emotion" not in str(scope_messages)


@pytest.mark.parametrize("regulation", ["gdpr", "eu_data_act", "dora", "dsa", "cra_dma_nis2"])
@pytest.mark.parametrize(
    "article_no", ["Article 78", "eu_ai_act_art78", "Article 59", "eu_ai_act_art59"]
)
def test_activity_check_does_not_change_other_adapters(regulation, article_no):
    code = "publish(document);"
    model = _model(code, article_no)
    expected = json.loads(model.invoke.return_value.content)["findings"]
    pack = get_regulation_pack(regulation)

    kept = validator_call.call_validator(
        candidates=[{"description": "Unprotected document publication."}],
        enriched_code=code,
        file_label="publish.py",
        model=model,
        regulation_pack=pack,
        timeout_s=9.0,
    )

    assert kept == expected
    assert model.invoke.call_count == 1
    assert model.invoke.call_args.kwargs["timeout_s"] == 9.0
    assert model.invoke.call_args.args[0][0]["content"] == (
        pack.validator_system + "\n" + validator_call._EVIDENCE_INSTRUCTIONS
    )


@pytest.mark.parametrize("article_no", ["eu_ai_act_art78", "eu_ai_act_art59"])
def test_rejecting_scoped_article_preserves_other_findings_in_the_same_chunk(article_no):
    code = "publish(document);"
    model = _model(code, article_no)
    payload = json.loads(model.invoke.return_value.content)
    other_finding = {**payload["findings"][0], "article_no": "eu_ai_act_art5"}
    payload["findings"].append(other_finding)
    model.invoke.side_effect = [
        SimpleNamespace(content=json.dumps(payload)),
        SimpleNamespace(content='{"activity":"ordinary_activity"}'),
    ]

    assert _validate(code, model) == [other_finding]


@pytest.mark.parametrize("article_no", ["eu_ai_act_art78", "eu_ai_act_art59"])
@pytest.mark.parametrize("response", ['{"activity":"unknown"}', "{}", "not JSON"])
def test_invalid_activity_response_fails_the_validation(response, article_no):
    code = "publish(document);"
    model = _model(code, article_no)
    model.invoke.side_effect = [model.invoke.return_value, SimpleNamespace(content=response)]

    with pytest.raises(ValueError, match="invalid findings or source evidence"):
        _validate(code, model)


@pytest.mark.parametrize("article_no", ["eu_ai_act_art78", "eu_ai_act_art59"])
def test_activity_check_uses_remaining_time_budget(monkeypatch, article_no):
    ticks = iter([100.0, 103.0])
    monkeypatch.setattr(validator_call.time, "monotonic", lambda: next(ticks))
    code = "publish(document);"
    model = _model(code, article_no)
    model.invoke.side_effect = [
        model.invoke.return_value,
        SimpleNamespace(content='{"activity":"ai_act_duties"}'),
    ]

    assert len(_validate(code, model, timeout_s=10.0)) == 1
    assert model.invoke.call_args.kwargs["timeout_s"] == 7.0


@pytest.mark.parametrize("article_no", ["eu_ai_act_art78", "eu_ai_act_art59"])
def test_activity_check_cannot_start_after_budget_expires(monkeypatch, article_no):
    ticks = iter([100.0, 111.0])
    monkeypatch.setattr(validator_call.time, "monotonic", lambda: next(ticks))
    model = _model("publish(document);", article_no)

    with pytest.raises(ValueError) as error:
        _validate("publish(document);", model, timeout_s=10.0)
    assert isinstance(error.value.__cause__, TimeoutError)
    assert model.invoke.call_count == 1


@pytest.mark.parametrize(
    "activities,expected_articles",
    [
        (("ai_act_duties", "ordinary_activity"), ["eu_ai_act_art5", "eu_ai_act_art78"]),
        (("ordinary_activity", "ai_act_duties"), ["eu_ai_act_art5", "eu_ai_act_art59"]),
        (("ordinary_activity", "ordinary_activity"), ["eu_ai_act_art5"]),
    ],
)
def test_mixed_scopes_are_checked_independently_with_one_budget(
    monkeypatch, activities, expected_articles
):
    ticks = iter([100.0, 103.0, 105.0])
    monkeypatch.setattr(validator_call.time, "monotonic", lambda: next(ticks))
    code = "publish(document);"
    model = _model(code)
    template = json.loads(model.invoke.return_value.content)["findings"][0]
    findings = [
        {**template, "article_no": article}
        for article in ("eu_ai_act_art5", "eu_ai_act_art78", "eu_ai_act_art59")
    ]
    model.invoke.side_effect = [
        SimpleNamespace(content=json.dumps({"findings": findings})),
        *(SimpleNamespace(content=json.dumps({"activity": a})) for a in activities),
    ]

    kept = _validate(code, model, timeout_s=10.0)

    assert [f["article_no"] for f in kept] == expected_articles
    calls = model.invoke.call_args_list
    assert [call.kwargs["timeout_s"] for call in calls] == [10.0, 7.0, 5.0]
    assert calls[1].args[0][0]["content"] == validator_call._ARTICLE78_ACTIVITY
    assert calls[2].args[0][0]["content"] == validator_call._ARTICLE59_ACTIVITY


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
