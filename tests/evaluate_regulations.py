"""Run the local models against regulation fixtures, separately from pytest.

Run from the repository root:
    PYTHONPATH=src python tests/evaluate_regulations.py --regulation gdpr \
        --models-dir /path/to/models --output /tmp/regulation-baseline.jsonl

Labels and rationales are used only for scoring, never sent to either model.
Synthetic fixtures are not executed. A control means no defect is established
in the excerpt, not that an entire product has been certified compliant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from contextlib import ExitStack
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

# Evaluate this checkout even when the virtualenv also contains a released wheel.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from precommiteu.detector_call import call_detector
from precommiteu.direct import _as_added_diff
from precommiteu.grammar import DETECTOR_GBNF, VALIDATOR_GBNF
from precommiteu.llama_server import launch_llama_server
from precommiteu.model_factory import build_chat_model
from precommiteu.regulations import get_regulation_pack
from precommiteu.src.scanner import _normalize_validator_article_id
from precommiteu.validator_call import call_validator


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class RecordedModel:
    def __init__(self, model):
        self.model = model
        self.responses = []

    def invoke(self, messages, **kwargs):
        response = self.model.invoke(messages, **kwargs)
        self.responses.append(response.content)
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--regulation",
        required=True,
        choices=("gdpr", "eu_data_act", "dora", "dsa", "cra_dma_nis2"),
    )
    parser.add_argument(
        "--pack-ref", help="Load the selected pack prompts from a trusted local git revision"
    )
    parser.add_argument(
        "--validator-file", type=Path, help="Trusted local experimental validator entry point"
    )
    parser.add_argument(
        "--detector-instructions", type=Path, help="Experimental detector instruction suffix"
    )
    parser.add_argument(
        "--validator-instructions", type=Path, help="Experimental validator instruction suffix"
    )
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, action="append")
    parser.add_argument("--case", action="append", help="Evaluate only these case IDs")
    parser.add_argument(
        "--candidates-from",
        type=Path,
        action="append",
        help="Replay recorded detector candidates to isolate validator changes; repeatable",
    )
    parser.add_argument(
        "--validator-ref",
        help="Load only validator_call.py from a trusted local git revision; "
        "all other pipeline files still come from this checkout",
    )
    parser.add_argument("--wall-seconds", type=float, default=90.0)
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after a runtime error; the partial run cannot pass comparison",
    )
    args = parser.parse_args()
    fixture_paths = args.fixtures or [
        Path(__file__).parent / "fixtures/regulations" / args.regulation / "development.json"
    ]
    rows = [row for path in fixture_paths for row in json.loads(path.read_text())]
    if len({row["id"] for row in rows}) != len(rows):
        parser.error("fixture IDs must be unique")
    if args.case:
        rows = [r for r in rows if r["id"] in args.case]
        if {r["id"] for r in rows} != set(args.case):
            parser.error("unknown case ID")
    replay = {}
    for path in args.candidates_from or []:
        additional = {
            r["id"]: r
            for line in path.read_text().splitlines()
            if (r := json.loads(line)).get("type") == "case"
        }
        if replay.keys() & additional.keys():
            parser.error("duplicate recorded candidate case IDs")
        replay.update(additional)
    if args.candidates_from and not {row["id"] for row in rows} <= replay.keys():
        parser.error("missing recorded candidates for selected fixtures")
    base = args.models_dir / "base.gguf"
    adapter = args.models_dir / args.regulation / "detector-adapter.gguf"
    if not base.is_file() or not adapter.is_file():
        parser.error("both base model and selected detector adapter are required")
    pack = get_regulation_pack(args.regulation)
    if args.pack_ref:
        prefix = subprocess.check_output(["git", "rev-parse", "--show-prefix"], text=True).strip()
        values = {}
        for field, name in (
            ("detector_system", "detector_summary.md"),
            ("validator_system", "validator_summary.md"),
            ("regulations_summary", "regulations_summary.md"),
        ):
            path = f"{prefix}src/precommiteu/regulations/{args.regulation}/{name}"
            values[field] = subprocess.check_output(
                ["git", "show", f"{args.pack_ref}:{path}"],
                text=True,
            )
        pack = replace(pack, **values)
    if args.detector_instructions:
        pack = replace(
            pack,
            detector_system=pack.detector_system + "\n" + args.detector_instructions.read_text(),
        )
    if args.validator_instructions:
        pack = replace(
            pack,
            validator_system=pack.validator_system + "\n" + args.validator_instructions.read_text(),
        )
    validate = call_validator
    validator_path = Path("src/precommiteu/validator_call.py")
    validator_source = validator_path.read_bytes()
    if args.validator_ref and args.validator_file:
        parser.error("choose either --validator-ref or --validator-file")
    if args.validator_ref:
        prefix = subprocess.check_output(["git", "rev-parse", "--show-prefix"], text=True).strip()
        validator_source = subprocess.check_output(
            [
                "git",
                "show",
                f"{args.validator_ref}:{prefix}{validator_path}",
            ]
        )
    if args.validator_file:
        validator_source = args.validator_file.read_bytes()
    if args.validator_ref or args.validator_file:
        baseline_module = ModuleType("_evaluation_baseline_validator")
        sys.modules[baseline_module.__name__] = baseline_module
        exec(compile(validator_source, str(validator_path), "exec"), baseline_module.__dict__)
        validate = baseline_module.call_validator
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "type": "metadata",
        "regulation": args.regulation,
        "started_at": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "fixture_sha256": {str(p): sha256(p) for p in fixture_paths},
        "base_sha256": sha256(base),
        "adapter_sha256": sha256(adapter),
        "temperature": 0,
        "n_ctx": 32768,
        "max_tokens": 8192,
        "wall_seconds": args.wall_seconds,
        "fail_fast": args.fail_fast,
        "llama_server": subprocess.check_output(
            ["llama-server", "--version"], stderr=subprocess.STDOUT, text=True
        ).strip(),
        "candidates_from": [str(path) for path in args.candidates_from or []],
        "candidates_sha256": {str(path): sha256(path) for path in args.candidates_from or []},
        "pack_ref": args.pack_ref,
        "validator_ref": args.validator_ref,
        "validator_file": str(args.validator_file) if args.validator_file else None,
        "validator_source_sha256": hashlib.sha256(validator_source).hexdigest(),
        "experimental_instructions": {
            str(p): sha256(p)
            for p in (args.detector_instructions, args.validator_instructions)
            if p
        },
        "detector_prompt_sha256": hashlib.sha256(pack.detector_system.encode()).hexdigest(),
        "validator_prompt_sha256": hashlib.sha256(pack.validator_system.encode()).hexdigest(),
        "source_sha256": {
            str(p): sha256(p)
            for p in (
                Path("src/precommiteu/validator_call.py"),
                Path("src/precommiteu/detector_call.py"),
                Path("src/precommiteu/grammar.py"),
                Path("src/precommiteu/regulations/__init__.py"),
                Path("src/precommiteu/regulations/adapter_checks.py"),
                Path("src/precommiteu/regulations/eu_ai_act/validation_context.py"),
                Path(__file__),
                *sorted((Path("src/precommiteu/regulations") / args.regulation).glob("*.py")),
                *sorted((Path("src/precommiteu/regulations") / args.regulation).glob("*.md")),
            )
        },
    }
    with args.output.open("x") as output, ExitStack() as stack:
        output.write(json.dumps(metadata) + "\n")
        output.flush()
        print(
            "Starting local base model"
            + (
                " with recorded detector candidates"
                if args.candidates_from
                else " and selected adapter"
            ),
            flush=True,
        )
        handle = stack.enter_context(launch_llama_server(base, n_gpu_layers=99))
        validator = RecordedModel(build_chat_model(handle, grammar=VALIDATOR_GBNF))
        detector = None
        if not args.candidates_from:
            handle = stack.enter_context(
                launch_llama_server(base, n_gpu_layers=99, lora_path=adapter)
            )
            detector = RecordedModel(build_chat_model(handle, grammar=DETECTOR_GBNF))
        correct = 0
        for index, row in enumerate(rows, 1):
            result = {
                "type": "case",
                "id": row["id"],
                "article": row["article"],
                "expected_articles": row["expected_articles"],
                "candidates": [],
                "findings": [],
                "error": None,
            }
            validator.responses.clear()
            if detector is not None:
                detector.responses.clear()
            start = time.monotonic()
            diff = _as_added_diff(row["file"], row["code"])
            stage = "detector"
            try:
                result["candidates"] = (
                    replay[row["id"]]["candidates"]
                    if replay
                    else call_detector(
                        diff, detector, regulation_pack=pack, timeout_s=args.wall_seconds
                    )
                )
                result["detector_seconds"] = round(time.monotonic() - start, 3)
                stage = "validator"
                result["findings"] = validate(
                    result["candidates"],
                    diff,
                    row["file"],
                    validator,
                    regulation_pack=pack,
                    timeout_s=args.wall_seconds - (time.monotonic() - start),
                )
            except Exception as exc:
                result["error"] = f"{stage}: {type(exc).__name__}: {exc}"
            result["seconds"] = round(time.monotonic() - start, 3)
            result["validator_responses"] = list(validator.responses)
            result["detector_responses"] = list(detector.responses) if detector else []
            actual = sorted(
                {
                    _normalize_validator_article_id(f["article_no"], pack.name)
                    for f in result["findings"]
                }
            )
            result["actual_articles"] = actual
            result["correct"] = actual == sorted(row["expected_articles"]) and not result["error"]
            correct += result["correct"]
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            print(
                f"{index}/{len(rows)} {row['id']}: "
                f"{'PASS' if result['correct'] else 'FAIL'} "
                f"candidates={len(result['candidates'])} articles={actual} "
                f"{result['seconds']}s {result['error'] or ''}",
                flush=True,
            )
            if args.fail_fast and result["error"]:
                raise RuntimeError(f"evaluation stopped after {row['id']}: {result['error']}")
        output.write(json.dumps({"type": "summary", "correct": correct, "total": len(rows)}) + "\n")
        print(f"Exact case matches: {correct}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
