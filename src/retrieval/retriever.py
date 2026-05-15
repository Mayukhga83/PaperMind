from __future__ import annotations

from collections import defaultdict

from src.config import AppConfig
from src.retrieval.evidence_selector import select_diverse_evidence
from src.retrieval.embeddings import OpenAIEmbedder
from src.retrieval.lexical import BM25Index
from src.retrieval.reranker import BGEReranker
from src.retrieval.vector_store import PaperVectorStore
from src.schemas.domain import ChunkRecord, RetrievedEvidence
from src.schemas.outputs import RetrievalPlan


MODE_PRIORS: dict[str, dict[str, float]] = {
    "Ask with Citations": {
        "result": 0.025,
        "method": 0.015,
        "discussion": 0.015,
    },
    "Verify Claim": {
        "result": 0.035,
        "discussion": 0.025,
        "limitation": 0.02,
    },
    "Extract Research Gaps": {
        "limitation": 0.07,
        "future_work": 0.07,
        "discussion": 0.035,
        "evaluation": 0.02,
    },
    "Generate Ideas": {
        "limitation": 0.06,
        "future_work": 0.06,
        "method": 0.025,
        "result": 0.025,
        "discussion": 0.025,
    },
}


def _chunk_from_row(row: dict) -> ChunkRecord:
    meta = row["metadata"]
    return ChunkRecord(
        chunk_id=str(meta.get("chunk_id") or row["chunk_id"]),
        doc_id=str(meta["doc_id"]),
        doc_title=str(meta["doc_title"]),
        file_name=str(meta["file_name"]),
        page_start=int(meta["page_start"]),
        page_end=int(meta["page_end"]),
        section=str(meta.get("section", "Unspecified")),
        chunk_type=str(meta.get("chunk_type", "unknown")),
        token_count=int(meta.get("token_count", 0)),
        text=str(row["document"]),
    )


class HybridRetriever:
    def __init__(
        self,
        config: AppConfig,
        vector_store: PaperVectorStore,
        embedder: OpenAIEmbedder,
    ) -> None:
        self.config = config
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = BGEReranker(config.reranker_model)

    def retrieve(
        self,
        mode: str,
        user_input: str,
        plan: RetrievalPlan,
    ) -> list[RetrievedEvidence]:
        all_rows = self.vector_store.all_chunks()
        lexical = BM25Index(all_rows)
        candidates: dict[str, dict] = {}
        rrf_scores: defaultdict[str, float] = defaultdict(float)
        dense_scores: defaultdict[str, float] = defaultdict(float)
        lexical_scores: defaultdict[str, float] = defaultdict(float)
        matched_queries: defaultdict[str, list[str]] = defaultdict(list)
        query_vectors = self.embedder.embed_queries(plan.queries)

        for query in plan.queries:
            dense_rows = self.vector_store.dense_query(
                query_vectors[query], self.config.dense_results_per_query
            )
            for rank, row in enumerate(dense_rows, start=1):
                chunk_id = row["chunk_id"]
                candidates[chunk_id] = row
                rrf_scores[chunk_id] += 1.0 / (60 + rank)
                dense_scores[chunk_id] = max(dense_scores[chunk_id], row["score"])
                matched_queries[chunk_id].append(query)

            for row in lexical.search(query, self.config.lexical_results):
                chunk_id = row["chunk_id"]
                candidates[chunk_id] = row
                rrf_scores[chunk_id] += 1.0 / (60 + int(row["lexical_rank"]))
                lexical_scores[chunk_id] = max(
                    lexical_scores[chunk_id], float(row["lexical_score"])
                )
                matched_queries[chunk_id].append(query)

        if not candidates:
            return []

        max_rrf = max(rrf_scores.values()) or 1.0
        priors = MODE_PRIORS.get(mode, {})
        ranked_rows: list[tuple[str, float]] = []
        for chunk_id, row in candidates.items():
            chunk_type = str(row["metadata"].get("chunk_type", "unknown"))
            normalized_rrf = rrf_scores[chunk_id] / max_rrf
            fused = (
                0.55 * normalized_rrf
                + 0.3 * dense_scores[chunk_id]
                + 0.15 * lexical_scores[chunk_id]
                + priors.get(chunk_type, 0.0)
            )
            if chunk_type == "references":
                fused -= 0.12
            ranked_rows.append((chunk_id, fused))
        ranked_rows.sort(key=lambda item: item[1], reverse=True)
        ranked_rows = ranked_rows[: self.config.candidate_limit]

        evidence_candidates: list[RetrievedEvidence] = []
        for chunk_id, fused in ranked_rows:
            row = candidates[chunk_id]
            evidence_candidates.append(
                RetrievedEvidence(
                    evidence_id="",
                    chunk=_chunk_from_row(row),
                    dense_score=dense_scores[chunk_id],
                    lexical_score=lexical_scores[chunk_id],
                    fusion_score=fused,
                    matched_queries=list(dict.fromkeys(matched_queries[chunk_id])),
                )
            )

        rerank_query = f"Task: {mode}\nResearch request: {user_input}"
        rerank_scores = self.reranker.score(
            rerank_query, [item.chunk.text for item in evidence_candidates]
        )
        for item, score in zip(evidence_candidates, rerank_scores, strict=True):
            item.rerank_score = score
        evidence_candidates.sort(
            key=lambda item: (item.rerank_score, item.fusion_score), reverse=True
        )
        preselected = evidence_candidates[: max(self.config.final_evidence_count * 3, 20)]
        embeddings = self.vector_store.fetch_embeddings(
            [item.chunk.chunk_id for item in preselected]
        )
        return select_diverse_evidence(
            preselected,
            embeddings,
            self.config.final_evidence_count,
        )


def evidence_packet(evidence: list[RetrievedEvidence]) -> str:
    blocks: list[str] = []
    for item in evidence:
        chunk = item.chunk
        blocks.append(
            "\n".join(
                [
                    f"[{item.evidence_id}]",
                    f"Paper: {chunk.doc_title}",
                    f"Source: {chunk.citation_label}",
                    f"Section: {chunk.section}",
                    f"Chunk type: {chunk.chunk_type}",
                    f"Chunk ID: {chunk.chunk_id}",
                    "Evidence text:",
                    chunk.text,
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)
