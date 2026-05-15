from src.ingestion.section_detector import classify_chunk_type, detect_heading


def test_detect_known_and_numbered_heading() -> None:
    assert detect_heading("4.2 Limitations") == "Limitations"
    assert detect_heading("FUTURE WORK") == "Future Work"
    assert detect_heading("This is an ordinary sentence.") is None


def test_classify_chunk_type() -> None:
    assert classify_chunk_type("Limitations", "The sample is small.") == "limitation"
    assert classify_chunk_type("Methods", "We introduce an algorithm.") == "method"
