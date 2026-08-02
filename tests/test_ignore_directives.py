from __future__ import annotations

from precommiteu.src.eu_ignore_marker import (
    match_eu_ignore_marker_in_range,
    parse_eu_ignore_markers,
)
from precommiteu.src.ignore_directives import (
    apply_prompt_ignore_directives,
    has_prompt_ignore_file_directive,
)


def test_ignore_file_directive_drops_the_whole_file(risky_code):
    text = "# eu-ignore-file\n" + (risky_code / "models.py").read_text(encoding="utf-8")

    assert has_prompt_ignore_file_directive(text)
    assert apply_prompt_ignore_directives(text) is None


def test_ignore_next_line_blanks_only_the_following_line():
    text = "keep_a = 1\n# eu-ignore-next-line\nemail = user.email\nkeep_b = 2\n"

    assert apply_prompt_ignore_directives(text) == "keep_a = 1\n\n\nkeep_b = 2\n"


def test_ignore_next_lines_blanks_the_requested_count():
    text = "# eu-ignore-next-lines: 2\na = 1\nb = 2\nc = 3\n"

    assert apply_prompt_ignore_directives(text) == "\n\n\nc = 3\n"


def test_ignore_start_end_blanks_the_enclosed_block():
    text = "a = 1\n# eu-ignore-start\nssn = x\ndob = y\n# eu-ignore-end\nb = 2\n"

    assert apply_prompt_ignore_directives(text) == "a = 1\n\n\n\n\nb = 2\n"


def test_directive_name_must_match_on_word_boundaries():
    text = "url = 'https://x/eu-ignore-file-list'\nemail = user.email\n"

    assert not has_prompt_ignore_file_directive(text)
    assert apply_prompt_ignore_directives(text) == text


def test_inline_marker_parses_rule_reason_and_line():
    text = 'a = 1\nb = 2  # precommiteu-ignore: gdpr_art32 reason="test fixture"\n'

    markers = parse_eu_ignore_markers(text)

    assert len(markers) == 1
    assert (markers[0].rule, markers[0].reason, markers[0].line_no) == (
        "gdpr_art32",
        "test fixture",
        2,
    )


def test_inline_marker_without_reason_is_ignored():
    assert parse_eu_ignore_markers("x = 1  # precommiteu-ignore: gdpr_art32\n") == []


def test_inline_wildcard_marker_is_rejected():
    text = 'x = 1  # precommiteu-ignore: * reason="blanket"\n'

    assert parse_eu_ignore_markers(text) == []


def test_marker_matches_article_within_radius_and_not_outside():
    markers = parse_eu_ignore_markers(
        'x = 1  # precommiteu-ignore: gdpr_art* reason="reviewed"\n'
    )

    assert match_eu_ignore_marker_in_range("gdpr_art32", 2, 3, markers) is not None
    assert match_eu_ignore_marker_in_range("gdpr_art32", 50, 51, markers) is None
    assert match_eu_ignore_marker_in_range("dora_art9", 1, 1, markers) is None
    assert match_eu_ignore_marker_in_range(None, 1, 1, markers) is None
