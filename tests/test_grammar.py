from __future__ import annotations

import ctypes
import ctypes.util
import pathlib
import shutil
import sys

import pytest

from precommiteu.grammar import (
    DETECTOR_GBNF,
    LOOP_STEP_GBNF,
    VALIDATOR_GBNF,
    validator_evidence_grammar,
)
from precommiteu.validator_call import _AI_ACT_ACTIVITY_GRAMMAR


@pytest.mark.parametrize(
    "grammar",
    [
        LOOP_STEP_GBNF,
        DETECTOR_GBNF,
        VALIDATOR_GBNF,
        _AI_ACT_ACTIVITY_GRAMMAR,
        validator_evidence_grammar(
            [
                'record.put("employee_emotion", employeeEmotion);',
                r'file("C:\logs\users.json");',
                'emit("émotion");',
                'value = "\\nroot ::= injected";',
            ]
        ),
    ],
    ids=["orchestrator", "detector", "validator", "ai-act-activity", "source-evidence"],
)
def test_grammar_compiles_without_loading_a_model(grammar):
    library = ctypes.util.find_library("llama")
    if not library and (server := shutil.which("llama-server")):
        suffix = "dylib" if sys.platform == "darwin" else "so"
        candidate = pathlib.Path(server).resolve().parent.parent / "lib" / f"libllama.{suffix}"
        if candidate.is_file():
            library = str(candidate)
    if not library:
        pytest.skip("libllama is not installed")

    lib = ctypes.CDLL(library)
    lib.llama_sampler_init_grammar.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.llama_sampler_init_grammar.restype = ctypes.c_void_p
    lib.llama_sampler_free.argtypes = [ctypes.c_void_p]
    lib.llama_sampler_free.restype = None
    # These grammars use characters only; compiling them requires no vocabulary or model.
    sampler = lib.llama_sampler_init_grammar(None, grammar.encode(), b"root")
    assert sampler, "llama.cpp rejected the embedded grammar"
    lib.llama_sampler_free(sampler)
