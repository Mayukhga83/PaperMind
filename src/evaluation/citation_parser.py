from __future__ import annotations

import re

EVIDENCE_ID = re.compile(r"\bE\d+\b", re.IGNORECASE)


def normalize_evidence_id(value: str) -> str:
    match = EVIDENCE_ID.search(value.strip())
    return match.group(0).upper() if match else ""


def extract_evidence_ids(text: str) -> list[str]:
    return list(dict.fromkeys(match.upper() for match in EVIDENCE_ID.findall(text)))


def cited_sentences(markdown: str) -> list[tuple[str, list[str]]]:
    normalized = re.sub(r"\s+", " ", markdown).strip()
    if not normalized:
        return []
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9*])", normalized)
    output: list[tuple[str, list[str]]] = []
    for sentence in sentences:
        ids = extract_evidence_ids(sentence)
        if ids:
            output.append((sentence.strip(), ids))
    return output
