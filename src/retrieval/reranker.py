from __future__ import annotations

from functools import lru_cache

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    model.to("cpu")
    return tokenizer, model


class BGEReranker:
    def __init__(self, model_name: str, batch_size: int = 8, max_length: int = 1024) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        tokenizer, model = _load_model(self.model_name)
        scores: list[float] = []
        with torch.inference_mode():
            for start in range(0, len(documents), self.batch_size):
                batch = documents[start : start + self.batch_size]
                pairs = [[query, document] for document in batch]
                inputs = tokenizer(
                    pairs,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                )
                logits = model(**inputs).logits.view(-1).float().cpu().numpy()
                normalized = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
                scores.extend(float(value) for value in normalized)
        return scores
