"""Run the local models against the AI Act fixtures, separately from pytest.

Run from the repository root:
    PYTHONPATH=src python tests/evaluate_ai_act.py --models-dir /path/to/models \
        --output /tmp/ai-act-baseline.jsonl

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
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, action="append")
    parser.add_argument("--case", action="append", help="Evaluate only these case IDs")
    parser.add_argument("--candidates-from", type=Path,
                        help="Replay recorded detector candidates to isolate validator changes")
    parser.add_argument("--validator-ref",
                        help="Load only validator_call.py from a trusted local git revision; "
                             "all other pipeline files still come from this checkout")
    parser.add_argument("--wall-seconds", type=float, default=90.0)
    parser.add_argument("--fail-fast", action="store_true",
                        help="Stop after a runtime error; the partial run cannot pass comparison")
    args = parser.parse_args()
    fixture_paths = args.fixtures or [Path(__file__).parent / "fixtures/ai_act" / name
                                    for name in ("article_pairs.json", "challenges.json",
                                                 "scope_regressions.json",
                                                 "validation_variants.json",
                                                 "context_boundaries.json")]
    rows = [row for path in fixture_paths for row in json.loads(path.read_text())]
    if len({row["id"] for row in rows}) != len(rows):
        parser.error("fixture IDs must be unique")
    if args.case:
        rows = [r for r in rows if r["id"] in args.case]
        if {r["id"] for r in rows} != set(args.case):
            parser.error("unknown case ID")
    replay = {}
    if args.candidates_from:
        replay = {r["id"]: r for line in args.candidates_from.read_text().splitlines()
                  if (r := json.loads(line)).get("type") == "case"}
    base = args.models_dir / "base.gguf"
    adapter = args.models_dir / "eu_ai_act/detector-adapter.gguf"
    if not base.is_file() or not adapter.is_file():
        parser.error("both base model and AI Act detector adapter are required")
    pack = get_regulation_pack("eu_ai_act")
    validate = call_validator
    validator_path = Path("src/precommiteu/validator_call.py")
    validator_source = validator_path.read_bytes()
    if args.validator_ref:
        prefix = subprocess.check_output(["git", "rev-parse", "--show-prefix"], text=True).strip()
        validator_source = subprocess.check_output([
            "git", "show", f"{args.validator_ref}:{prefix}{validator_path}",
        ])
        baseline_module = ModuleType("_evaluation_baseline_validator")
        sys.modules[baseline_module.__name__] = baseline_module
        exec(compile(validator_source, str(validator_path), "exec"), baseline_module.__dict__)
        validate = baseline_module.call_validator
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "type": "metadata", "started_at": datetime.now(UTC).isoformat(),
        "platform": platform.platform(), "python": platform.python_version(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "fixture_sha256": {str(p): sha256(p) for p in fixture_paths}, "base_sha256": sha256(base),
        "adapter_sha256": sha256(adapter), "temperature": 0, "n_ctx": 32768,
        "max_tokens": 8192, "wall_seconds": args.wall_seconds,
        "fail_fast": args.fail_fast,
        "llama_server": subprocess.check_output(["llama-server", "--version"],
                                                 stderr=subprocess.STDOUT, text=True).strip(),
        "candidates_from": str(args.candidates_from) if args.candidates_from else None,
        "candidates_sha256": sha256(args.candidates_from) if args.candidates_from else None,
        "validator_ref": args.validator_ref,
        "validator_source_sha256": hashlib.sha256(validator_source).hexdigest(),
        "source_sha256": {str(p): sha256(p) for p in (
            Path("src/precommiteu/validator_call.py"),
            Path("src/precommiteu/detector_call.py"),
            Path("src/precommiteu/grammar.py"),
            Path(__file__),
            *sorted(Path("src/precommiteu/regulations/eu_ai_act").glob("*.py")),
            *sorted(Path("src/precommiteu/regulations/eu_ai_act").glob("*.md")),
        )},
    }
    with args.output.open("x") as output, ExitStack() as stack:
        output.write(json.dumps(metadata) + "\n")
        output.flush()
        print("Starting local base model" + (
            " with recorded detector candidates" if args.candidates_from else " and AI Act adapter"
        ), flush=True)
        handle = stack.enter_context(launch_llama_server(base, n_gpu_layers=99))
        validator = RecordedModel(build_chat_model(handle, grammar=VALIDATOR_GBNF))
        detector = None
        if not args.candidates_from:
            handle = stack.enter_context(launch_llama_server(base, n_gpu_layers=99,
                                                           lora_path=adapter))
            detector = RecordedModel(build_chat_model(handle, grammar=DETECTOR_GBNF))
        correct = 0
        for index, row in enumerate(rows, 1):
            result = {"type": "case", "id": row["id"], "article": row["article"],
                      "expected_articles": row["expected_articles"],
                      "candidates": [], "findings": [], "error": None}
            validator.responses.clear()
            if detector is not None:
                detector.responses.clear()
            start = time.monotonic()
            diff = _as_added_diff(row["file"], row["code"])
            stage = "detector"
            try:
                result["candidates"] = (replay[row["id"]]["candidates"] if replay else
                    call_detector(diff, detector, regulation_pack=pack,
                                  timeout_s=args.wall_seconds))
                result["detector_seconds"] = round(time.monotonic() - start, 3)
                stage = "validator"
                result["findings"] = validate(
                    result["candidates"], diff, row["file"], validator,
                    regulation_pack=pack,
                    timeout_s=args.wall_seconds - (time.monotonic() - start),
                )
            except Exception as exc:
                result["error"] = f"{stage}: {type(exc).__name__}: {exc}"
            result["seconds"] = round(time.monotonic() - start, 3)
            result["validator_responses"] = list(validator.responses)
            result["detector_responses"] = list(detector.responses) if detector else []
            actual = sorted({_normalize_validator_article_id(f["article_no"], pack.name)
                             for f in result["findings"]})
            result["actual_articles"] = actual
            result["correct"] = actual == sorted(row["expected_articles"]) and not result["error"]
            correct += result["correct"]
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            print(f'{index}/{len(rows)} {row["id"]}: '
                  f'{"PASS" if result["correct"] else "FAIL"} '
                  f'candidates={len(result["candidates"])} articles={actual} '
                  f'{result["seconds"]}s {result["error"] or ""}', flush=True)
            if args.fail_fast and result["error"]:
                raise RuntimeError(f"evaluation stopped after {row['id']}: {result['error']}")
        output.write(json.dumps({"type": "summary", "correct": correct,
                                 "total": len(rows)}) + "\n")
        print(f"Exact case matches: {correct}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
