from __future__ import annotations

import re

KNOWN_SECTIONS = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "background": "Background",
    "related work": "Related Work",
    "literature review": "Literature Review",
    "method": "Method",
    "methods": "Methods",
    "methodology": "Methodology",
    "materials and methods": "Materials and Methods",
    "data": "Data",
    "dataset": "Dataset",
    "datasets": "Datasets",
    "experimental setup": "Experimental Setup",
    "experiments": "Experiments",
    "evaluation": "Evaluation",
    "results": "Results",
    "analysis": "Analysis",
    "discussion": "Discussion",
    "limitations": "Limitations",
    "limitation": "Limitations",
    "future work": "Future Work",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "references": "References",
    "appendix": "Appendix",
}

_NUMBERED_HEADING = re.compile(
    r"^(?:\d+(?:\.\d+){0,3}|[IVXLC]+)[.)]?\s+([A-Za-z][^.!?]{1,90})$"
)


def normalize_heading(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip(" .:\t\n")
    value = re.sub(r"^(?:\d+(?:\.\d+){0,3}|[IVXLC]+)[.)]?\s+", "", value)
    return value


def detect_heading(line: str) -> str | None:
    raw = re.sub(r"\s+", " ", line).strip()
    if not raw or len(raw) > 100 or len(raw.split()) > 12:
        return None

    normalized = normalize_heading(raw)
    lower = normalized.lower()
    if lower in KNOWN_SECTIONS:
        return KNOWN_SECTIONS[lower]

    numbered = _NUMBERED_HEADING.match(raw)
    if numbered:
        candidate = normalize_heading(numbered.group(1))
        if len(candidate.split()) <= 10:
            return candidate.title() if candidate.isupper() else candidate

    letters = [char for char in raw if char.isalpha()]
    if letters and raw.upper() == raw and 1 <= len(raw.split()) <= 8:
        return normalized.title()

    words = normalized.split()
    if 1 <= len(words) <= 7:
        title_like = sum(
            word[:1].isupper() or word.lower() in {"and", "of", "the", "for", "in"}
            for word in words
        )
        if title_like == len(words) and not raw.endswith(('.', '?', '!')):
            return normalized
    return None


def classify_chunk_type(section: str, text: str) -> str:
    section_lower = section.lower().strip()
    section_rules = [
        ("references", ("reference", "bibliography")),
        ("limitation", ("limitation", "threat to validity")),
        ("future_work", ("future work", "future research")),
        ("dataset", ("dataset", "data", "corpus", "annotation")),
        ("evaluation", ("evaluation", "metric", "benchmark")),
        ("method", ("method", "methodology", "approach", "architecture")),
        ("experiment", ("experiment", "experimental setup")),
        ("result", ("result", "finding")),
        ("discussion", ("discussion", "implication")),
        ("background", ("introduction", "background", "related work", "literature")),
    ]
    for label, terms in section_rules:
        if any(term in section_lower for term in terms):
            return label

    content = text[:1400].lower()
    content_rules = [
        ("references", ("references", "bibliography")),
        ("limitation", ("limitation", "weakness", "shortcoming", "threat to validity")),
        ("future_work", ("future work", "future research", "we plan to", "remains to")),
        ("dataset", ("dataset", "corpus", "data collection", "annotation")),
        ("evaluation", ("evaluation", "metric", "benchmark", "measure")),
        ("method", ("method", "methodology", "approach", "algorithm", "architecture")),
        ("experiment", ("experiment", "experimental setup", "baseline", "hyperparameter")),
        ("result", ("result", "finding", "we observe", "outperform", "performance")),
        ("discussion", ("discussion", "implication", "interpretation")),
        ("background", ("introduction", "background", "related work", "literature")),
    ]
    for label, terms in content_rules:
        if any(term in content for term in terms):
            return label
    return "unknown"
