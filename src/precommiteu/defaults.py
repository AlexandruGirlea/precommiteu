from __future__ import annotations

import os
import pathlib

from precommiteu.config import MODELS_DIR_ENV

MISSING_MODELS_HINT = (
    f"pass --models-dir (or set {MODELS_DIR_ENV}) pointing at the directory "
    "holding the precommitEU model bundle (expected layout: base.gguf, "
    "orchestrator.gguf, <regulation>/detector-adapter.gguf); see docs/install.md "
    "for how to get the bundle"
)


def model_bundle(
    models_root: pathlib.Path | None, regulations: tuple[str, ...]
) -> tuple[pathlib.Path, pathlib.Path, dict[str, pathlib.Path]]:
    root = models_root or os.environ.get(MODELS_DIR_ENV)
    if not root:
        raise ValueError(f"no model paths configured; {MISSING_MODELS_HINT}")
    root = pathlib.Path(root).expanduser()
    orchestrator = root / "orchestrator.gguf"
    detector = root / "base.gguf"
    adapters = {r: root / r / "detector-adapter.gguf" for r in regulations}
    for path in (orchestrator, detector, *adapters.values()):
        if not path.is_file():
            raise ValueError(f"required path not found: {path}")
    if orchestrator.samefile(detector):
        raise ValueError("orchestrator.gguf and base.gguf must be separate models")
    return orchestrator, detector, adapters

