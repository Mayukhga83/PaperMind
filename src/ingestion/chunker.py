from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

import tiktoken

from src.ingestion.section_detector import classify_chunk_type, detect_heading
from src.schemas.domain import ChunkRecord, PageRecord


@lru_cache(maxsize=1)
def _encoding() -> Optional[tiktoken.Encoding]:
    for name in ("o200k_base", "cl100k_base"):
        try:
            return tiktoken.get_encoding(name)
        except Exception:
            continue
    return None


def count_tokens(text: str) -> int:
    encoding = _encoding()
    if encoding is not None:
        return len(encoding.encode(text))
    return max(len(text) // 4, len(text.split()))


def _paragraphs(page: PageRecord, inherited_section: str) -> tuple[list[dict], str]:
    section = inherited_section or "Unspecified"
    blocks: list[dict] = []
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = " ".join(buffer).strip()
        if text:
            blocks.append(
                {"text": text, "page": page.page_number, "section": section}
            )
        buffer = []

    for raw in page.text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            flush()
            continue
        heading = detect_heading(line)
        if heading:
            flush()
            section = heading
            continue
        buffer.append(line)
        if line.endswith(('.', '!', '?', ':')) and count_tokens(" ".join(buffer)) >= 80:
            flush()
    flush()
    return blocks, section


def _split_oversized(block: dict, target_tokens: int) -> list[dict]:
    if count_tokens(block["text"]) <= target_tokens:
        return [block]
    sentences = re.split(r"(?<=[.!?])\s+", block["text"])
    pieces: list[dict] = []
    current: list[str] = []
    for sentence in sentences:
        prospective = " ".join(current + [sentence]).strip()
        if current and count_tokens(prospective) > target_tokens:
            pieces.append({**block, "text": " ".join(current)})
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        pieces.append({**block, "text": " ".join(current)})
    return pieces


def _overlap_tail(blocks: list[dict], overlap_tokens: int) -> list[dict]:
    selected: list[dict] = []
    total = 0
    for block in reversed(blocks):
        tokens = count_tokens(block["text"])
        if not selected and tokens > overlap_tokens:
            break
        if selected and total + tokens > overlap_tokens:
            break
        selected.append(block)
        total += tokens
    return list(reversed(selected))


def chunk_pages(
    pages: list[PageRecord],
    target_tokens: int = 900,
    overlap_tokens: int = 170,
) -> list[ChunkRecord]:
    if not pages:
        return []
    all_blocks: list[dict] = []
    section = "Unspecified"
    for page in pages:
        page_blocks, section = _paragraphs(page, section)
        for block in page_blocks:
            all_blocks.extend(_split_oversized(block, target_tokens))

    chunks: list[ChunkRecord] = []
    current: list[dict] = []
    current_tokens = 0

    def emit() -> None:
        nonlocal current, current_tokens
        if not current:
            return
        text = "\n\n".join(block["text"] for block in current).strip()
        if not text:
            current = []
            current_tokens = 0
            return
        page_start = min(block["page"] for block in current)
        page_end = max(block["page"] for block in current)
        section_name = current[-1]["section"] or "Unspecified"
        number = len(chunks) + 1
        chunk_id = f"{pages[0].doc_id}_p{page_start}_c{number}"
        chunks.append(
            ChunkRecord(
                chunk_id=chunk_id,
                doc_id=pages[0].doc_id,
                doc_title=pages[0].doc_title,
                file_name=pages[0].file_name,
                page_start=page_start,
                page_end=page_end,
                section=section_name,
                chunk_type=classify_chunk_type(section_name, text),
                token_count=count_tokens(text),
                text=text,
            )
        )
        current = _overlap_tail(current, overlap_tokens)
        current_tokens = sum(count_tokens(block["text"]) for block in current)

    for block in all_blocks:
        block_tokens = count_tokens(block["text"])
        section_changed = current and block["section"] != current[-1]["section"]
        would_overflow = current and current_tokens + block_tokens > target_tokens
        if section_changed or would_overflow:
            emit()
        current.append(block)
        current_tokens += block_tokens
    emit()

    unique: list[ChunkRecord] = []
    seen: set[str] = set()
    for chunk in chunks:
        fingerprint = re.sub(r"\s+", " ", chunk.text).strip().lower()
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(chunk)
    return unique
