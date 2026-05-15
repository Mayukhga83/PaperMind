from __future__ import annotations

import re

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+", text.lower())


class BM25Index:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.corpus = [tokenize(row["document"]) for row in rows]
        self.model = BM25Okapi(self.corpus) if self.corpus else None

    def search(self, query: str, limit: int) -> list[dict]:
        if self.model is None:
            return []
        scores = self.model.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
        positive = [idx for idx in ranked if scores[idx] > 0][:limit]
        if not positive:
            return []
        max_score = max(float(scores[idx]) for idx in positive) or 1.0
        output: list[dict] = []
        for rank, idx in enumerate(positive, start=1):
            row = dict(self.rows[idx])
            row["lexical_score"] = float(scores[idx]) / max_score
            row["lexical_rank"] = rank
            output.append(row)
        return output
