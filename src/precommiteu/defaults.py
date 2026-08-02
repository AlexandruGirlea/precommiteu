from __future__ import annotations

import os
import pathlib

from precommiteu.config import MODELS_DIR_ENV

MISSING_MODELS_HINT = (
    f"pass --models-dir (or set {MODELS_DIR_ENV}) pointing at the directory "
    "holding the precommitEU model bundle (expected layout: base.gguf, "
    "<regulation>/detector-adapter.gguf), or pass explicit "
    "--orchestrator-model / --detector-adapter paths; see docs/install.md "
    "for how to get the bundle"
)


def models_dir(override: pathlib.Path | None = None) -> pathlib.Path | None:
    if override is not None:
        return override.expanduser()
    value = os.environ.get(MODELS_DIR_ENV)
    return pathlib.Path(value).expanduser() if value else None


def default_orchestrator_model(
    models_root: pathlib.Path | None = None,
) -> pathlib.Path | None:
    root = models_dir(models_root)
    return root / "base.gguf" if root else None


def default_detector_adapter(
    regulation: str, models_root: pathlib.Path | None = None
) -> pathlib.Path | None:
    root = models_dir(models_root)
    return root / regulation / "detector-adapter.gguf" if root else None


