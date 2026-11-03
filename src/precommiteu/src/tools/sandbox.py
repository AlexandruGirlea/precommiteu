from __future__ import annotations

from pathlib import Path

from precommiteu.src.file_filter import SKIP_DIR_NAMES, is_eu_ignored

__all__ = ["Sandbox"]


class Sandbox:
    def __init__(
        self, roots: tuple[Path, ...], *, excluded_paths: tuple[Path, ...] = (),
    ) -> None:
        if not roots:
            raise ValueError("Sandbox requires at least one root")
        self._roots: tuple[Path, ...] = tuple(
            Path(r).expanduser().resolve() for r in roots
        )
        self._excluded_paths = tuple(
            Path(p).expanduser().resolve() for p in excluded_paths
        )

    @property
    def roots(self) -> tuple[Path, ...]:
        return self._roots

    def resolve(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        resolved = (candidate if candidate.is_absolute() else self._roots[0] / candidate).resolve()
        if any(resolved.is_relative_to(p) for p in self._excluded_paths):
            raise PermissionError(f"path {resolved} is excluded from context")
        for root in self._roots:
            try:
                rel = resolved.relative_to(root)
            except ValueError:
                continue
            else:
                dirs = rel.parts if resolved.is_dir() else rel.parts[:-1]
                if SKIP_DIR_NAMES.intersection(p.lower() for p in dirs):
                    raise PermissionError(
                        f"path {resolved} is in a skipped directory"
                    )
                if is_eu_ignored(resolved, root):
                    raise PermissionError(
                        f"path {resolved} is excluded by .eu-ignore"
                    )
                return resolved
        raise PermissionError(
            f"path {resolved} is outside sandbox roots {[str(r) for r in self._roots]}"
        )
