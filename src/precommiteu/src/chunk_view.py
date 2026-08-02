from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CanonicalChunk", "ChunkConsultLog"]


@dataclass(frozen=True)
class CanonicalChunk:
    id: str
    file: str
    start_line: int
    end_line: int
    text: str


class ChunkConsultLog:
    def __init__(self) -> None:
        self._order: list[str] = []
        self._seen_texts: set[str] = set()
        self._keys: list[str] = []

    def record(self, chunk_id_or_path: str, text: str) -> None:
        if text in self._seen_texts:
            return
        self._seen_texts.add(text)
        self._order.append(text)
        self._keys.append(chunk_id_or_path)

    def consulted_text(self) -> str:
        return "\n".join(self._order)
