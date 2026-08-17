from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
from datetime import UTC, datetime

from pydantic import ValidationError

from precommiteu.src.schemas import Advisory, Finding

__all__ = ["FORMAT_VERSION", "ScanLedger", "default_ledger_path"]

FORMAT_VERSION = 1

_LOG = logging.getLogger(__name__)


def default_ledger_path(target: pathlib.Path, regulation: str) -> pathlib.Path:
    # Never inside the scanned tree: a scan writes nothing into the target.
    digest = hashlib.sha256(str(pathlib.Path(target).resolve()).encode()).hexdigest()
    return (
        pathlib.Path.home()
        / ".precommiteu"
        / "scans"
        / f"{regulation}-{digest[:16]}.json"
    )


def _sha256(path: pathlib.Path) -> str:
    try:
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except OSError:
        return ""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class ScanLedger:
    def __init__(
        self,
        path: pathlib.Path,
        target: pathlib.Path,
        regulation: str,
        entries: dict[str, dict] | None = None,
    ) -> None:
        self.path = path
        self.target = target
        self.regulation = regulation
        self.entries = entries if entries is not None else {}
        self._save_failed = False

    @classmethod
    def load(
        cls,
        target: pathlib.Path,
        regulation: str,
        path: pathlib.Path | None = None,
    ) -> ScanLedger:
        target = pathlib.Path(target).resolve()
        if path is None:
            path = default_ledger_path(target, regulation)
        ledger = cls(pathlib.Path(path), target, regulation)
        try:
            doc = json.loads(ledger.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ledger
        if (
            not isinstance(doc, dict)
            or doc.get("version") != FORMAT_VERSION
            or doc.get("regulation") != regulation
            or doc.get("target") != str(target)
            or not isinstance(doc.get("files"), dict)
        ):
            _LOG.info("scan ledger at %s not reusable; scanning everything", path)
            return ledger
        ledger.entries = {
            rel: entry
            for rel, entry in doc["files"].items()
            if isinstance(entry, dict) and (target / rel).exists()
        }
        return ledger

    def stamp(self, rel: str) -> dict[str, object] | None:
        try:
            stat = (self.target / rel).stat()
        except OSError:
            return None
        return {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": _sha256(self.target / rel),
        }

    def reuse(self, rel: str) -> tuple[list[Finding], list[Advisory]] | None:
        entry = self.entries.get(rel)
        if entry is None:
            return None
        path = self.target / rel
        try:
            stat = path.stat()
        except OSError:
            del self.entries[rel]
            return None
        if stat.st_size != entry.get("size") or stat.st_mtime_ns != entry.get("mtime_ns"):
            # mtime moves without the bytes moving (checkout, touch, sync), so
            # a hash decides before we spend minutes of inference again.
            if not entry.get("sha256") or _sha256(path) != entry["sha256"]:
                del self.entries[rel]
                return None
            entry["size"] = stat.st_size
            entry["mtime_ns"] = stat.st_mtime_ns
        try:
            return (
                [Finding(**f) for f in entry.get("findings", [])],
                [Advisory(**a) for a in entry.get("advisories", [])],
            )
        except (TypeError, ValidationError):
            del self.entries[rel]
            return None

    def record(
        self,
        rel: str,
        stamp: dict[str, object] | None,
        findings: list[Finding],
        advisories: list[Advisory],
    ) -> None:
        if stamp is None or not stamp["sha256"]:
            return
        self.entries[rel] = {
            **stamp,
            "scanned_at": _now(),
            "findings": [f.model_dump(mode="json") for f in findings],
            "advisories": [a.model_dump(mode="json") for a in advisories],
        }

    def save(self) -> None:
        doc = {
            "version": FORMAT_VERSION,
            "regulation": self.regulation,
            "target": str(self.target),
            "updated_at": _now(),
            "files": self.entries,
        }
        tmp = self.path.with_name(f"{self.path.name}.tmp.{os.getpid()}")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(doc), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            if not self._save_failed:
                self._save_failed = True
                _LOG.warning(
                    "cannot write the scan ledger at %s (%s); this scan will "
                    "not be reusable",
                    self.path,
                    exc,
                )
