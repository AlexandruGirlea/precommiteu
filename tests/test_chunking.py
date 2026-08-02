from __future__ import annotations

from itertools import pairwise

from precommiteu.chunking import (
    APPROX_TOKENS,
    USER_MESSAGE_TOKEN_BUDGET,
    token_chunks,
    truncate_to_token_budget,
)


def test_chunks_cover_every_line_without_gaps(risky_code):
    path = risky_code / "CrmSyncJob.java"
    text = path.read_text(encoding="utf-8")

    chunks = token_chunks(path, text)

    assert chunks
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == len(text.splitlines())
    for previous, current in pairwise(chunks):
        assert current.start_line == previous.end_line + 1
    assert "".join(c.text for c in chunks) == text


def test_chunk_id_encodes_file_and_line_range(risky_code):
    path = risky_code / "models.py"

    chunk = token_chunks(path, path.read_text(encoding="utf-8"))[0]

    assert chunk.id == f"{path}:{chunk.start_line}-{chunk.end_line}"
    assert chunk.file == str(path)


def test_empty_file_yields_no_chunks(tmp_path):
    assert token_chunks(tmp_path / "empty.py", "") == []


def test_truncate_leaves_text_within_budget_untouched():
    text = "short enough\n"

    assert truncate_to_token_budget(text, USER_MESSAGE_TOKEN_BUDGET) == text


def test_truncate_marks_and_shrinks_oversized_text():
    text = "x" * 100_000

    truncated = truncate_to_token_budget(text, 100)

    assert truncated.endswith("[...TRUNCATED...]")
    assert len(truncated) < len(text)
    assert APPROX_TOKENS(truncated) <= 100
