from __future__ import annotations

from src.reasoning.llm_client import OpenAIReasoner
from src.retrieval.retriever import evidence_packet
from src.schemas.domain import RetrievedEvidence
from src.schemas.outputs import ClaimVerificationResult
from src.schemas.prompts import CLAIM_PROMPT


def verify_claim(
    reasoner: OpenAIReasoner,
    claim: str,
    evidence: list[RetrievedEvidence],
) -> ClaimVerificationResult:
    prompt = f"""
Claim to verify:
{claim}

Retrieved evidence:
{evidence_packet(evidence)}

Judge the exact claim rather than a loosely related statement. Include inline evidence IDs in
the explanation. Each supporting or contradicting point must list its evidence IDs.
""".strip()
    return reasoner.parse(
        system_prompt=CLAIM_PROMPT,
        user_prompt=prompt,
        output_schema=ClaimVerificationResult,
        max_output_tokens=6500,
    )
