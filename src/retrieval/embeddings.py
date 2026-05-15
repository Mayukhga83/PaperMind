from __future__ import annotations

from collections.abc import Iterable

from openai import OpenAI


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = self.client.embeddings.create(model=self.model, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend(item.embedding for item in ordered)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=[text])
        return response.data[0].embedding

    def embed_queries(self, texts: Iterable[str]) -> dict[str, list[float]]:
        items = list(dict.fromkeys(texts))
        vectors = self.embed_documents(items)
        return dict(zip(items, vectors, strict=True))
