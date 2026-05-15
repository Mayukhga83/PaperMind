from __future__ import annotations

import re
from typing import Any

from src.evaluation.citation_parser import extract_evidence_ids, normalize_evidence_id
from src.evaluation.faithfulness_checker import audit_claims, fallback_assessments
from src.schemas.domain import RetrievedEvidence
from src.schemas.outputs import (
    AnswerResult,
    ClaimVerificationResult,
    FaithfulnessResult,
    GapResult,
    IdeaResult,
)

ResultType = AnswerResult | ClaimVerificationResult | GapResult | IdeaResult


def _claims_from_result(result: ResultType) -> list[tuple[str, list[str]]]:
    claims: list[tuple[str, list[str]]] = []
    if isinstance(result, AnswerResult):
        claims.extend((item.claim, item.citations) for item in result.key_claims)
        if not claims:
            claims.extend(
                (sentence, extract_evidence_ids(sentence))
                for sentence in re.split(r"(?<=[.!?])\s+", result.answer_markdown)
                if extract_evidence_ids(sentence)
            )
    elif isinstance(result, ClaimVerificationResult):
        claims.extend((item.claim, item.citations) for item in result.supporting_points)
        claims.extend((item.claim, item.citations) for item in result.contradicting_points)
    elif isinstance(result, GapResult):
        claims.extend((f"{item.title}: {item.description}", item.citations) for item in result.gaps)
    elif isinstance(result, IdeaResult):
        claims.extend(
            (
                f"{item.title}: {item.grounding_from_papers}",
                item.citations,
            )
            for item in result.ideas
        )
    normalized: list[tuple[str, list[str]]] = []
    for claim, citations in claims:
        if not claim.strip():
            continue
        ids = [normalize_evidence_id(item) for item in citations]
        normalized.append((claim.strip(), [item for item in ids if item]))
    return normalized


def citation_audit(
    result: ResultType,
    evidence: list[RetrievedEvidence],
    reasoner,
    limit: int = 24,
) -> dict[str, Any]:
    valid_ids = {item.evidence_id for item in evidence}
    claims = _claims_from_result(result)
    cited_claims = [item for item in claims if item[1]]
    unknown_ids = sorted(
        {
            citation
            for _, citations in claims
            for citation in citations
            if citation not in valid_ids
        }
    )
    coverage = len(cited_claims) / len(claims) if claims else 1.0
    used_ids = {citation for _, citations in cited_claims for citation in citations if citation in valid_ids}
    source_map = {item.evidence_id: item.chunk.doc_id for item in evidence}
    unique_sources = {source_map[citation] for citation in used_ids if citation in source_map}

    try:
        faithfulness: FaithfulnessResult = audit_claims(
            reasoner, claims, evidence, limit=limit
        )
        semantic_status = "completed"
    except Exception as exc:
        faithfulness = fallback_assessments(claims, valid_ids)
        semantic_status = f"fallback: {exc}"

    checkable = [
        item for item in faithfulness.assessments if item.verdict != "not_checkable"
    ]
    supported = [
        item
        for item in checkable
        if item.verdict in {"supported", "partially_supported"}
    ]
    support_rate = len(supported) / len(checkable) if checkable else 1.0
    return {
        "claims": claims,
        "citation_coverage": coverage,
        "unknown_ids": unknown_ids,
        "evidence_used": sorted(used_ids),
        "unique_sources": len(unique_sources),
        "support_rate": support_rate,
        "semantic_status": semantic_status,
        "assessments": faithfulness.assessments,
    }
