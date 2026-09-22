from __future__ import annotations

import pytest

from precommiteu.scan import _references_siblings


@pytest.mark.parametrize(
    "text,expected",
    [
        ('URI.create("https://ai.example/models/emotions/predict")', False),
        ('URI.create("http://localhost:9000/models/predict?source=models")', False),
        ("from models import User", True),
        ("new Helper().infer(frame);", True),
        ('URI.create("https://ai.example/models");\nnew Helper();', True),
    ],
)
def test_urls_do_not_count_as_sibling_dependencies(tmp_path, text, expected):
    target = tmp_path / "job.java"
    target.write_text(text)
    (tmp_path / "models.py").write_text("class User: pass\n")
    (tmp_path / "Helper.java").write_text("class Helper {}\n")

    assert _references_siblings(text, target) is expected


def test_crm_emotion_endpoint_does_not_route_to_models_py(risky_code):
    target = risky_code / "CrmSyncJob.java"
    assert not _references_siblings(target.read_text(encoding="utf-8"), target)
