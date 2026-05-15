from __future__ import annotations

import math

import numpy as np

from src.schemas.domain import RetrievedEvidence


def _cosine(left: list[float], right: list[float]) -> float:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def select_diverse_evidence(
    candidates: list[RetrievedEvidence],
    embeddings: dict[str, list[float]],
    limit: int,
) -> list[RetrievedEvidence]:
    remaining = list(candidates)
    selected: list[RetrievedEvidence] = []
    while remaining and len(selected) < limit:
        best: RetrievedEvidence | None = None
        best_score = -math.inf
        for candidate in remaining:
            base = 0.78 * candidate.rerank_score + 0.22 * candidate.fusion_score
            same_source = sum(
                item.chunk.doc_id == candidate.chunk.doc_id for item in selected
            )
            same_section = sum(
                item.chunk.doc_id == candidate.chunk.doc_id
                and item.chunk.section == candidate.chunk.section
                for item in selected
            )
            same_page = sum(
                item.chunk.doc_id == candidate.chunk.doc_id
                and item.chunk.page_start == candidate.chunk.page_start
                for item in selected
            )
            source_bonus = 0.06 if selected and same_source == 0 else 0.0
            section_penalty = 0.035 * same_section
            page_penalty = 0.07 * same_page
            redundancy = 0.0
            candidate_vector = embeddings.get(candidate.chunk.chunk_id)
            if candidate_vector and selected:
                similarities = []
                for item in selected:
                    other = embeddings.get(item.chunk.chunk_id)
                    if other:
                        similarities.append(_cosine(candidate_vector, other))
                redundancy = max(similarities, default=0.0)
            score = base + source_bonus - section_penalty - page_penalty - 0.18 * max(0.0, redundancy)
            if score > best_score:
                best_score = score
                best = candidate
        if best is None:
            break
        best.selection_score = best_score
        selected.append(best)
        remaining.remove(best)

    for index, evidence in enumerate(selected, start=1):
        evidence.evidence_id = f"E{index}"
    return selected
