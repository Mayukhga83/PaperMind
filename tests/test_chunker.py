from src.ingestion import chunker
from src.schemas.domain import PageRecord


def test_chunker_produces_unique_page_aware_chunks(monkeypatch) -> None:
    monkeypatch.setattr(chunker, "_encoding", lambda: None)
    paragraph = " ".join(["This sentence describes a research method."] * 35)
    pages = [
        PageRecord(
            doc_id="P1",
            doc_title="Test Paper",
            file_name="test.pdf",
            page_number=1,
            text=f"1 Introduction\n\n{paragraph}\n\n2 Limitations\n\n{paragraph}",
        )
    ]
    chunks = chunker.chunk_pages(pages, target_tokens=150, overlap_tokens=30)
    assert chunks
    assert len({item.text for item in chunks}) == len(chunks)
    assert all(item.doc_id == "P1" for item in chunks)
    assert all(item.page_start == 1 for item in chunks)
