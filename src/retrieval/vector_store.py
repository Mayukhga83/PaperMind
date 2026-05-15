from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from src.schemas.domain import ChunkRecord


class PaperVectorStore:
    def __init__(self, directory: Path, collection_name: str = "papermind") -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(directory))
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            configuration={
                "hnsw": {
                    "space": "cosine",
                    "ef_construction": 200,
                    "ef_search": 160,
                }
            },
            metadata={"description": "PaperMind session evidence index"},
        )

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            configuration={"hnsw": {"space": "cosine", "ef_search": 160}},
            metadata={"description": "PaperMind session evidence index"},
        )

    def add(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding counts do not match.")
        if not chunks:
            return
        self.collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata() for chunk in chunks],
            embeddings=embeddings,
        )

    def dense_query(self, embedding: list[float], limit: int) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(limit, self.count()),
            include=["documents", "metadatas", "distances"],
        )
        if not result.get("ids") or not result["ids"][0]:
            return []
        rows: list[dict[str, Any]] = []
        for chunk_id, document, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        ):
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "document": document,
                    "metadata": metadata,
                    "distance": float(distance),
                    "score": max(0.0, 1.0 - float(distance)),
                }
            )
        return rows

    def all_chunks(self, include_embeddings: bool = False) -> list[dict[str, Any]]:
        include = ["documents", "metadatas"]
        if include_embeddings:
            include.append("embeddings")
        result = self.collection.get(include=include)
        rows: list[dict[str, Any]] = []
        embeddings = result.get("embeddings")
        for index, chunk_id in enumerate(result.get("ids", [])):
            row = {
                "chunk_id": chunk_id,
                "document": result["documents"][index],
                "metadata": result["metadatas"][index],
            }
            if embeddings is not None:
                row["embedding"] = embeddings[index]
            rows.append(row)
        return rows

    def fetch_embeddings(self, chunk_ids: list[str]) -> dict[str, list[float]]:
        if not chunk_ids:
            return {}
        result = self.collection.get(ids=chunk_ids, include=["embeddings"])
        embeddings = result.get("embeddings")
        if embeddings is None:
            return {}
        return {
            chunk_id: list(vector)
            for chunk_id, vector in zip(result["ids"], embeddings, strict=True)
        }

    def count(self) -> int:
        return self.collection.count()
