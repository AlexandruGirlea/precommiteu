from __future__ import annotations

import pytest

from precommiteu.llama_server import parse_build

# Homebrew moved the build number behind a semver string in late 2026; the older
# shapes still ship in source builds and older bottles.
CASES = [
    ("version: 0.1.0-dev (build 10450, commit ece963f41)", 10450),
    ("version: 9570 (3ac3c20c9)", 9570),
    ("b4400", 4400),
]


@pytest.mark.parametrize(("raw", "build"), CASES)
def test_parse_build_known_shapes(raw: str, build: int) -> None:
    assert parse_build(f"{raw}\nbuilt with AppleClang 21.0.0.21000101") == build


def test_parse_build_rejects_noise() -> None:
    with pytest.raises(RuntimeError):
        parse_build("built with AppleClang 21.0.0.21000101 for Darwin arm64")
