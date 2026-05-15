from __future__ import annotations

from src.reasoning.llm_client import OpenAIReasoner
from src.retrieval.retriever import evidence_packet
from src.schemas.domain import RetrievedEvidence
from src.schemas.outputs import IdeaResult
from src.schemas.prompts import IDEA_PROMPT


def generate_ideas(
    reasoner: OpenAIReasoner,
    request: str,
    evidence: list[RetrievedEvidence],
) -> IdeaResult:
    prompt = f"""
User focus:
{request}

Retrieved evidence:
{evidence_packet(evidence)}

Generate 4 to 6 distinct research ideas. Keep ideas technically specific, evidence-grounded, and
honest about uncertainty. Do not include MVP scope or CV/demo value. Use evidence IDs in each
idea's citations and wherever factual paper claims appear in prose.
""".strip()
    return reasoner.parse(
        system_prompt=IDEA_PROMPT,
        user_prompt=prompt,
        output_schema=IdeaResult,
        max_output_tokens=9000,
    )
