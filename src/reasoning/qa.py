from __future__ import annotations

from src.reasoning.llm_client import OpenAIReasoner
from src.retrieval.retriever import evidence_packet
from src.schemas.domain import RetrievedEvidence
from src.schemas.outputs import AnswerResult
from src.schemas.prompts import QA_PROMPT


def answer_question(
    reasoner: OpenAIReasoner,
    question: str,
    evidence: list[RetrievedEvidence],
) -> AnswerResult:
    prompt = f"""
User question:
{question}

Retrieved evidence:
{evidence_packet(evidence)}

Write a clear citation-grounded answer. Keep inline evidence identifiers in the answer_markdown.
List the main auditable factual claims in key_claims with their supporting evidence IDs.
""".strip()
    return reasoner.parse(
        system_prompt=QA_PROMPT,
        user_prompt=prompt,
        output_schema=AnswerResult,
        max_output_tokens=6000,
    )
