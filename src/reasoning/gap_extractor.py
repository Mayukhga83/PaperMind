from __future__ import annotations

from src.reasoning.llm_client import OpenAIReasoner
from src.retrieval.retriever import evidence_packet
from src.schemas.domain import RetrievedEvidence
from src.schemas.outputs import GapResult
from src.schemas.prompts import GAP_PROMPT


def extract_gaps(
    reasoner: OpenAIReasoner,
    request: str,
    evidence: list[RetrievedEvidence],
) -> GapResult:
    prompt = f"""
User focus:
{request}

Retrieved evidence:
{evidence_packet(evidence)}

Identify a concise set of distinct, well-supported research gaps. Cite every gap. Explain when
a gap is directly stated versus cautiously inferred across evidence passages.
""".strip()
    return reasoner.parse(
        system_prompt=GAP_PROMPT,
        user_prompt=prompt,
        output_schema=GapResult,
        max_output_tokens=7500,
    )
