from src.evaluation.citation_parser import (
    cited_sentences,
    extract_evidence_ids,
    normalize_evidence_id,
)


def test_extract_and_normalize_evidence_ids() -> None:
    assert extract_evidence_ids("Claim [E2, e4] and E2 again.") == ["E2", "E4"]
    assert normalize_evidence_id("[e17]") == "E17"
    assert normalize_evidence_id("nothing") == ""


def test_cited_sentences() -> None:
    rows = cited_sentences("First grounded claim [E1]. Second claim [E2, E3].")
    assert rows == [
        ("First grounded claim [E1].", ["E1"]),
        ("Second claim [E2, E3].", ["E2", "E3"]),
    ]
