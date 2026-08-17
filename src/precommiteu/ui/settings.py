from __future__ import annotations

import json
import os
import pathlib

from precommiteu.config import MODELS_DIR_ENV
from precommiteu.scan_ledger import default_ledger_path

STATE_DIR = pathlib.Path.home() / ".precommiteu-ui"
FILE = STATE_DIR / "settings.json"
KEYS = ("models_dir", "ledger_dir", "reports_dir")
# Only the file name is target-specific, so any target yields the same parent.
SCANS_DIR = default_ledger_path(pathlib.Path.home(), "gdpr").parent


def write_json(path: pathlib.Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def defaults() -> dict[str, pathlib.Path]:
    env = os.environ.get(MODELS_DIR_ENV)
    return {
        "models_dir": (
            pathlib.Path(env).expanduser()
            if env
            else pathlib.Path.home() / ".precommiteu" / "models"
        ),
        "ledger_dir": SCANS_DIR,
        "reports_dir": STATE_DIR / "runs",
    }


def _stored() -> dict[str, str]:
    try:
        doc = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict):
        return {}
    return {k: v for k, v in doc.items() if k in KEYS and isinstance(v, str) and v}


def _value(key: str) -> pathlib.Path:
    stored = _stored().get(key)
    return pathlib.Path(stored) if stored else defaults()[key]


def models_dir() -> pathlib.Path:
    return _value("models_dir")


def runs_dir() -> pathlib.Path:
    return _value("reports_dir")


def ledger_path(target: pathlib.Path, regulation: str) -> pathlib.Path:
    return _value("ledger_dir") / default_ledger_path(target, regulation).name


def view() -> dict[str, dict]:
    stored, base = _stored(), defaults()
    return {
        key: {
            "value": stored.get(key) or str(base[key]),
            "default": str(base[key]),
            "custom": key in stored,
        }
        for key in KEYS
    }


def _usable_dir(raw: str) -> pathlib.Path:
    path = pathlib.Path(raw).expanduser().resolve()
    if not path.is_dir():
        if path.exists():
            raise ValueError(f"not a directory: {path}")
        # Creating a directory outside the user's own home is not ours to decide.
        # home() has to be resolved too, or /var vs /private/var reads as outside.
        if not path.is_relative_to(pathlib.Path.home().resolve()):
            raise ValueError(f"{path} does not exist; create it first")
        try:
            path.mkdir(parents=True)
        except OSError as exc:
            raise ValueError(f"cannot create {path}: {exc}") from exc
    if not os.access(path, os.W_OK):
        raise ValueError(f"not writable: {path}")
    return path


def update(changes: dict[str, str | None]) -> dict[str, dict]:
    doc = _stored()
    for key, raw in changes.items():
        if raw:
            doc[key] = str(_usable_dir(raw))
        else:
            doc.pop(key, None)
    write_json(FILE, doc)
    return view()
