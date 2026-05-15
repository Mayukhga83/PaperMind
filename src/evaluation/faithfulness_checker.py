from __future__ import annotations

from src.reasoning.llm_client import OpenAIReasoner
from src.schemas.domain import RetrievedEvidence
from src.schemas.outputs import CitationAssessment, FaithfulnessResult
from src.schemas.prompts import CITATION_AUDIT_PROMPT


def audit_claims(
    reasoner: OpenAIReasoner,
    claims: list[tuple[str, list[str]]],
    evidence: list[RetrievedEvidence],
    limit: int = 24,
) -> FaithfulnessResult:
    evidence_by_id = {item.evidence_id: item for item in evidence}
    audit_blocks: list[str] = []
    for index, (claim, citations) in enumerate(claims[:limit], start=1):
        passages: list[str] = []
        for citation in citations:
            item = evidence_by_id.get(citation)
            if item:
                passages.append(
                    f"[{citation}] {item.chunk.citation_label} {item.chunk.text}"
                )
        audit_blocks.append(
            f"Claim {index}: {claim}\nCitations: {', '.join(citations)}\n"
            f"Cited evidence:\n" + "\n".join(passages)
        )
    if not audit_blocks:
        return FaithfulnessResult(assessments=[])
    prompt = "\n\n---\n\n".join(audit_blocks)
    return reasoner.parse(
        system_prompt=CITATION_AUDIT_PROMPT,
        user_prompt=prompt,
        output_schema=FaithfulnessResult,
        max_output_tokens=6500,
    )


def fallback_assessments(
    claims: list[tuple[str, list[str]]], valid_ids: set[str]
) -> FaithfulnessResult:
    assessments: list[CitationAssessment] = []
    for claim, citations in claims:
        known = [citation for citation in citations if citation in valid_ids]
        verdict = "not_checkable" if not known else "partially_supported"
        assessments.append(
            CitationAssessment(
                claim=claim,
                citations=known,
                verdict=verdict,
                explanation="Automated semantic support checking was unavailable; only citation validity was checked.",
            )
        )
    return FaithfulnessResult(assessments=assessments)
