from __future__ import annotations

import pytest

from precommiteu.src.file_filter import collect_code_files
from precommiteu.tools import read_tools, regulation_tools
from precommiteu.tools.find_references import find_references
from precommiteu.tools.sandbox import Sandbox


@pytest.mark.parametrize("extension", ["vue", "svelte", "sql", "sh"])
def test_source_types_are_scanned_and_available_as_context(tmp_path, extension):
    path = tmp_path / f"app.{extension}"
    path.write_text("shared_value = 1\n")
    sandbox = Sandbox((tmp_path,))

    assert collect_code_files([tmp_path], tmp_path)[0] == [path.resolve()]
    assert "shared_value" in read_tools.read_file(sandbox, path.name)["text"]
    assert find_references(sandbox, "shared_value", tmp_path)[0]["file"] == str(path)


def test_repository_context_excludes_non_code_and_ignored_files(tmp_path):
    for name in ["app.py", "ignored.py", "README.md", "notes.txt", "data.json", "LICENSE"]:
        (tmp_path / name).write_text("shared_value = 1\n")
    (tmp_path / ".eu-ignore").write_text("ignored.py\n")
    sandbox = Sandbox((tmp_path,))

    for name in ["README.md", "notes.txt", "data.json", "LICENSE", "ignored.py"]:
        with pytest.raises(PermissionError):
            read_tools.read_file(sandbox, name)

    assert [entry["path"] for entry in read_tools.list_dir(sandbox, ".")["entries"]] == [
        str(tmp_path / "app.py"),
    ]
    assert read_tools.glob(sandbox, "*")["matches"] == [str(tmp_path / "app.py")]
    assert [hit["path"] for hit in read_tools.grep(sandbox, "shared_value")["results"]] == [
        str(tmp_path / "app.py"),
    ]


def test_regulation_reference_markdown_remains_readable(tmp_path):
    pack = tmp_path / "gdpr"
    pack.mkdir()
    (pack / "regulations_summary.md").write_text("## gdpr_art5\nArticle reference.\n")

    result = regulation_tools.read_article(Sandbox((tmp_path,)), tmp_path, "gdpr_art5")

    assert "Article reference." in result["text"]
