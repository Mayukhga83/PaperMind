from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PageRecord:
    doc_id: str
    doc_title: str
    file_name: str
    page_number: int
    text: str


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    doc_title: str
    file_name: str
    page_start: int
    page_end: int
    section: str
    chunk_type: str
    token_count: int
    text: str

    @property
    def citation_label(self) -> str:
        if self.page_start == self.page_end:
            return f"[{self.doc_id}, p. {self.page_start}]"
        return f"[{self.doc_id}, pp. {self.page_start}-{self.page_end}]"

    def metadata(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "file_name": self.file_name,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "section": self.section,
            "chunk_type": self.chunk_type,
            "token_count": self.token_count,
            "citation_label": self.citation_label,
        }


@dataclass(slots=True)
class RetrievedEvidence:
    evidence_id: str
    chunk: ChunkRecord
    dense_score: float = 0.0
    lexical_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0
    selection_score: float = 0.0
    matched_queries: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DocumentSummary:
    doc_id: str
    title: str
    file_name: str
    pages: int
    chunks: int
