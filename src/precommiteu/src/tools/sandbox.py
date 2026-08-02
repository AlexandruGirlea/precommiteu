from __future__ import annotations

from pathlib import Path

__all__ = ["Sandbox"]


class Sandbox:
    def __init__(self, roots: tuple[Path, ...]) -> None:
        if not roots:
            raise ValueError("Sandbox requires at least one root")
        self._roots: tuple[Path, ...] = tuple(
            Path(r).expanduser().resolve() for r in roots
        )

    @property
    def roots(self) -> tuple[Path, ...]:
        return self._roots

    def resolve(self, path: str | Path) -> Path:
        resolved = Path(path).expanduser().resolve()
        for root in self._roots:
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            else:
                return resolved
        raise PermissionError(
            f"path {resolved} is outside sandbox roots {[str(r) for r in self._roots]}"
        )
