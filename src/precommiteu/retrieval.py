from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass

from precommiteu.config import (
    BM25_B,
    BM25_K1,
    RETRIEVAL_DESCRIPTION_WEIGHT,
    RETRIEVAL_TOP_K,
)

__all__ = ["CaseIndex", "RetrievalVerdict", "tokenize_code", "tokenize_text"]

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_WORD_RE = re.compile(r"[a-z]{3,}")

_STOPWORDS = frozenset(
    """def class func function return import from package public private static
    void int str string bool boolean float double var val let const this self
    new for while if else elif end then begin do not and or none null nil true
    false try except catch finally raise throw throws print println fmt args
    kwargs main init the for with that have has from this code are was were
    been being its also can may use used using does fails fail without any
    which their there when where what such only into over under between
    """.split()
)

TOP_K = RETRIEVAL_TOP_K
DESCRIPTION_WEIGHT = RETRIEVAL_DESCRIPTION_WEIGHT


def _split_identifier(ident: str) -> list[str]:
    parts: list[str] = []
    for chunk in ident.split("_"):
        parts.extend(_CAMEL_RE.split(chunk))
    return [p.lower() for p in parts if len(p) >= 3]


def tokenize_code(code: str) -> list[str]:
    tokens: list[str] = []
    for ident in _IDENT_RE.findall(code):
        words = _split_identifier(ident)
        tokens.extend(w for w in words if w not in _STOPWORDS)
        if len(words) > 1:
            joined = ident.lower()
            if joined not in _STOPWORDS:
                tokens.append(joined)
    return tokens


def tokenize_text(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS]


@dataclass(frozen=True)
class RetrievalVerdict:
    verdict: str
    confidence: float
    similarity: float
    probable_article_id: str | None


class CaseIndex:
    def __init__(self, cases: list[dict]) -> None:
        self._cases = cases
        self._code_df: Counter[str] = Counter()
        self._desc_df: Counter[str] = Counter()
        code_lens = []
        desc_lens = []
        for case in cases:
            code_tf = case["code_tf"]
            desc_tf = case["desc_tf"]
            self._code_df.update(code_tf.keys())
            self._desc_df.update(desc_tf.keys())
            code_lens.append(sum(code_tf.values()))
            desc_lens.append(sum(desc_tf.values()))
        n = max(1, len(cases))
        self._avg_code_len = max(1.0, sum(code_lens) / n)
        self._avg_desc_len = max(1.0, sum(desc_lens) / n)

    @classmethod
    def loads(cls, text: str) -> CaseIndex:
        return cls([json.loads(line) for line in text.splitlines() if line.strip()])

    def __len__(self) -> int:
        return len(self._cases)

    def _idf(self, df: int) -> float:
        n = len(self._cases)
        return math.log(1.0 + (n - df + 0.5) / (df + 0.5))

    def _field_score(
        self,
        query: Counter[str],
        doc_tf: dict[str, int],
        df: Counter[str],
        avg_len: float,
    ) -> float:
        doc_len = sum(doc_tf.values())
        if not doc_len:
            return 0.0
        score = 0.0
        norm = BM25_K1 * (1.0 - BM25_B + BM25_B * doc_len / avg_len)
        for term, q_count in query.items():
            tf = doc_tf.get(term)
            if not tf:
                continue
            idf = self._idf(df[term])
            score += min(q_count, 3) * idf * (tf * (BM25_K1 + 1.0)) / (tf + norm)
        return score

    def score(self, code: str, description: str = "") -> RetrievalVerdict:
        code_query = Counter(tokenize_code(code))
        desc_query = Counter(tokenize_text(description))
        if not code_query and not desc_query:
            return RetrievalVerdict("inconclusive", 0.0, 0.0, None)

        scored: list[tuple[float, dict]] = []
        for case in self._cases:
            s = self._field_score(code_query, case["code_tf"], self._code_df, self._avg_code_len)
            if desc_query:
                s += DESCRIPTION_WEIGHT * self._field_score(
                    desc_query, case["desc_tf"], self._desc_df, self._avg_desc_len
                )
            if s > 0.0:
                scored.append((s, case))
        if not scored:
            return RetrievalVerdict("inconclusive", 0.0, 0.0, None)

        scored.sort(key=lambda item: -item[0])
        top = scored[:TOP_K]
        total = sum(s for s, _ in top)
        violation_mass = sum(s for s, c in top if c["label"] == "violation")
        confidence = violation_mass / total if total else 0.0

        self_score = self._field_score(
            code_query, dict(code_query), self._code_df, self._avg_code_len
        )
        if desc_query:
            self_score += DESCRIPTION_WEIGHT * self._field_score(
                desc_query, dict(desc_query), self._desc_df, self._avg_desc_len
            )
        similarity = min(1.0, top[0][0] / self_score) if self_score > 0 else 0.0

        article: str | None = None
        if confidence >= 0.5:
            articles = Counter(
                c["article_id"]
                for s, c in top
                if c["label"] == "violation" and c.get("article_id")
            )
            if articles:
                article = articles.most_common(1)[0][0]

        if confidence >= 0.65:
            verdict = "violation_pattern"
        elif confidence <= 0.35:
            verdict = "compliant_pattern"
        else:
            verdict = "inconclusive"
        return RetrievalVerdict(
            verdict, round(confidence, 4), round(similarity, 4), article
        )
