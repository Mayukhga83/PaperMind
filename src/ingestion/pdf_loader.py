from __future__ import annotations

import io
import re
from collections import Counter
from pathlib import Path
from typing import BinaryIO

import fitz

from src.schemas.domain import PageRecord


def _normalize_repeated_line(line: str) -> str:
    line = re.sub(r"\d+", "#", line.lower())
    return re.sub(r"\s+", " ", line).strip()


def _candidate_margin_lines(text: str, margin: int = 3) -> tuple[list[str], list[str]]:
    lines = [re.sub(r"\s+", " ", item).strip() for item in text.splitlines()]
    lines = [line for line in lines if line]
    return lines[:margin], lines[-margin:] if lines else []


def _detect_repeated_margins(raw_pages: list[str]) -> set[str]:
    counts: Counter[str] = Counter()
    for text in raw_pages:
        top, bottom = _candidate_margin_lines(text)
        for line in set(top + bottom):
            normalized = _normalize_repeated_line(line)
            if 2 <= len(normalized) <= 160:
                counts[normalized] += 1
    threshold = max(2, round(len(raw_pages) * 0.45))
    return {line for line, count in counts.items() if count >= threshold}


def _clean_page_text(text: str, repeated: set[str]) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        stripped = re.sub(r"[ \t]+", " ", line).strip()
        if not stripped:
            kept.append("")
            continue
        if _normalize_repeated_line(stripped) in repeated:
            continue
        if re.fullmatch(r"\d{1,4}", stripped):
            continue
        kept.append(stripped)
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"(?<=\w)-\n(?=\w)", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _infer_title(first_page: str, fallback: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in first_page.splitlines()]
    lines = [line for line in lines if line]
    abstract_index = next(
        (index for index, line in enumerate(lines) if line.lower().strip(" .:") == "abstract"),
        min(len(lines), 25),
    )
    search_lines = lines[:abstract_index] or lines[:25]
    candidates: list[tuple[float, str]] = []
    blocked = (
        "abstract",
        "arxiv",
        "doi",
        "university",
        "department",
        "conference",
        "proceedings",
        "copyright",
        "http",
        "@",
    )
    for index, line in enumerate(search_lines):
        words = line.split()
        lower = line.lower()
        if not (5 <= len(line) <= 220 and 2 <= len(words) <= 28):
            continue
        if any(marker in lower for marker in blocked):
            continue
        score = 100 - (index * 4) + min(len(words), 18)
        if not line.endswith((".", "?", "!")):
            score += 12
        if sum(word[:1].isupper() for word in words) >= max(2, len(words) // 2):
            score += 6
        candidates.append((score, line))
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return Path(fallback).stem.replace("_", " ").replace("-", " ").strip()


def extract_pdf(
    source: str | Path | bytes | BinaryIO,
    doc_id: str,
    file_name: str,
) -> tuple[str, list[PageRecord]]:
    if isinstance(source, (str, Path)):
        document = fitz.open(str(source))
    elif isinstance(source, bytes):
        document = fitz.open(stream=source, filetype="pdf")
    else:
        payload = source.read()
        if isinstance(source, io.BytesIO):
            source.seek(0)
        document = fitz.open(stream=payload, filetype="pdf")

    try:
        if document.page_count == 0:
            raise ValueError(f"{file_name} contains no pages.")
        raw_pages = [page.get_text("text", sort=True) for page in document]
    finally:
        document.close()

    title = _infer_title(raw_pages[0], file_name)
    repeated = _detect_repeated_margins(raw_pages)
    cleaned_pages = [_clean_page_text(text, repeated) for text in raw_pages]
    pages = [
        PageRecord(
            doc_id=doc_id,
            doc_title=title,
            file_name=file_name,
            page_number=index + 1,
            text=text,
        )
        for index, text in enumerate(cleaned_pages)
        if text.strip()
    ]
    if not pages:
        raise ValueError(
            f"No extractable text was found in {file_name}. Scanned PDFs require OCR, "
            "which is not enabled in this version."
        )
    return title, pages
