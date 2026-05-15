from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetrievalPlan(StrictModel):
    queries: list[str] = Field(min_length=2, max_length=8)
    rationale: str


class CitedClaim(StrictModel):
    claim: str
    citations: list[str] = Field(default_factory=list)


class AnswerResult(StrictModel):
    answer_markdown: str
    key_claims: list[CitedClaim] = Field(default_factory=list)
    evidence_path: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ClaimVerificationResult(StrictModel):
    verdict: Literal[
        "supported",
        "partially_supported",
        "contradicted",
        "insufficient_evidence",
    ]
    confidence: Literal["low", "medium", "high"]
    explanation_markdown: str
    supporting_points: list[CitedClaim] = Field(default_factory=list)
    contradicting_points: list[CitedClaim] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    evidence_path: list[str] = Field(default_factory=list)


class ResearchGap(StrictModel):
    title: str
    gap_type: Literal[
        "dataset",
        "evaluation",
        "method",
        "reasoning",
        "deployment",
        "safety",
        "theory",
        "other",
    ]
    description: str
    why_it_matters: str
    project_direction: str
    citations: list[str] = Field(default_factory=list)


class GapResult(StrictModel):
    synthesis: str
    gaps: list[ResearchGap] = Field(default_factory=list)
    evidence_path: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ResearchIdea(StrictModel):
    title: str
    research_problem: str
    grounding_from_papers: str
    novelty_angle: str
    technical_approach: str
    dataset_or_model_suggestion: str
    evaluation_plan: str
    risk_or_limitation: str
    citations: list[str] = Field(default_factory=list)


class IdeaResult(StrictModel):
    synthesis: str
    ideas: list[ResearchIdea] = Field(default_factory=list)
    evidence_path: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CitationAssessment(StrictModel):
    claim: str
    citations: list[str]
    verdict: Literal[
        "supported", "partially_supported", "unsupported", "not_checkable"
    ]
    explanation: str


class FaithfulnessResult(StrictModel):
    assessments: list[CitationAssessment] = Field(default_factory=list)
