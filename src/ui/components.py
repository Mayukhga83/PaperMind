from __future__ import annotations

import html
import json
from typing import Any

import pandas as pd
import streamlit as st

from src.schemas.domain import DocumentSummary, RetrievedEvidence
from src.schemas.outputs import (
    AnswerResult,
    ClaimVerificationResult,
    GapResult,
    IdeaResult,
)


def render_header() -> None:
    st.markdown(
        """
        <div class="pm-hero">
          <div class="pm-kicker">Research intelligence workspace</div>
          <div class="pm-title">PaperMind</div>
          <div class="pm-subtitle">Citation-Grounded Research Reasoning and Idea Generation Assistant</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_author_card() -> None:
    st.markdown(
        """
        <div class="pm-author-card">
          <div class="pm-author-label">Developed by</div>
          <div class="pm-author-details">
            <strong>Mayukh Das</strong>
            <span class="pm-author-divider">·</span>
            <span>TU Braunschweig</span>
            <span class="pm-author-divider">·</span>
            <a href="mailto:mayukh@ifis.cs.tu-bs.de">mayukh@ifis.cs.tu-bs.de</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_how_it_works(analysis_limit: int = 15) -> None:
    with st.expander("How PaperMind works", expanded=False):
        st.markdown(
            f"""
**1. Upload research papers**  
Add between one and five text-based PDF papers to create a temporary research corpus.

**2. Build the evidence index**  
PaperMind extracts page-aware sections, creates semantic embeddings, and indexes the papers for hybrid retrieval.

**3. Choose a reasoning task**  
Ask a cited question, verify a claim, extract research gaps, or generate ideas grounded in the uploaded papers.

**4. Inspect the evidence**  
Review the retrieved passages, evidence path, and citation-support audit behind the result.

**Public demo allowance:** each browser session can run up to {analysis_limit} analyses. Uploading, indexing, changing tasks, and exporting results do not use an analysis attempt.

*PaperMind combines structure-aware PDF processing, hybrid multi-query retrieval, BGE reranking, structured LLM analysis, and citation-faithfulness checking.*

**Privacy note:** uploaded files are processed temporarily for the current session. Do not upload confidential documents or documents you are not permitted to process.
            """
        )


def render_session_usage(used: int, limit: int) -> None:
    """Render the public-demo analysis allowance without resetting it."""
    safe_limit = max(1, limit)
    safe_used = min(max(0, used), safe_limit)
    remaining = max(0, safe_limit - safe_used)
    percentage = int((safe_used / safe_limit) * 100)

    st.markdown(
        f"""
        <div class="pm-usage-card">
          <div class="pm-usage-main">
            <span class="pm-usage-label">Session allowance</span>
            <span class="pm-usage-value">{safe_used} of {safe_limit} used</span>
          </div>
          <div class="pm-usage-remaining">{remaining} remaining</div>
        </div>
        <div class="pm-usage-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{percentage}">
          <div class="pm-usage-fill" style="width:{percentage}%"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if remaining == 0:
        st.error(
            f"You have reached the {safe_limit}-analysis limit for this browser session. "
            "Existing results and exports remain available."
        )
    elif remaining <= 5:
        st.warning(f"You have {remaining} analyses remaining in this session.")

def render_document_cards(documents: list[DocumentSummary]) -> None:
    if not documents:
        return
    st.markdown('<div class="pm-section-title">Indexed research corpus</div>', unsafe_allow_html=True)
    columns = st.columns(min(len(documents), 3))
    for index, document in enumerate(documents):
        column = columns[index % len(columns)]
        with column:
            st.markdown(
                f"""
                <div class="pm-card">
                  <div class="pm-card-title">{html.escape(document.doc_id)} · {html.escape(document.title)}</div>
                  <div class="pm-meta">{html.escape(document.file_name)}</div>
                  <div class="pm-meta" style="margin-top:.45rem">{document.pages} pages · {document.chunks} evidence chunks · Indexed</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_result(result: Any) -> None:
    if isinstance(result, AnswerResult):
        st.markdown(result.answer_markdown)
        if result.limitations:
            with st.expander("Scope and limitations"):
                for item in result.limitations:
                    st.markdown(f"- {item}")
        return

    if isinstance(result, ClaimVerificationResult):
        st.markdown(
            f'<div class="pm-verdict">{html.escape(result.verdict.replace("_", " "))} · {html.escape(result.confidence)} confidence</div>',
            unsafe_allow_html=True,
        )
        st.markdown(result.explanation_markdown)
        left, right = st.columns(2)
        with left:
            st.markdown("#### Supporting evidence")
            if result.supporting_points:
                for item in result.supporting_points:
                    st.markdown(f"- {item.claim} `{' '.join(item.citations)}`")
            else:
                st.caption("No supporting point was established.")
        with right:
            st.markdown("#### Contradicting or qualifying evidence")
            if result.contradicting_points:
                for item in result.contradicting_points:
                    st.markdown(f"- {item.claim} `{' '.join(item.citations)}`")
            else:
                st.caption("No contradicting point was established.")
        if result.caveats:
            with st.expander("Caveats"):
                for item in result.caveats:
                    st.markdown(f"- {item}")
        return

    if isinstance(result, GapResult):
        st.markdown(result.synthesis)
        for index, gap in enumerate(result.gaps, start=1):
            with st.container(border=True):
                st.markdown(f"### {index}. {gap.title}")
                st.caption(gap.gap_type.replace("_", " ").title())
                st.markdown(gap.description)
                st.markdown("**Why it matters**")
                st.markdown(gap.why_it_matters)
                st.markdown("**Possible research direction**")
                st.markdown(gap.project_direction)
                st.markdown(f"**Evidence:** `{' '.join(gap.citations)}`")
        return

    if isinstance(result, IdeaResult):
        st.markdown(result.synthesis)
        for index, idea in enumerate(result.ideas, start=1):
            fields = [
                ("Research problem", idea.research_problem),
                ("Grounding from papers", idea.grounding_from_papers),
                ("Novelty angle", idea.novelty_angle),
                ("Technical approach", idea.technical_approach),
                ("Dataset / model suggestion", idea.dataset_or_model_suggestion),
                ("Evaluation plan", idea.evaluation_plan),
                ("Risk or limitation", idea.risk_or_limitation),
            ]
            field_html = "".join(
                f'<div class="pm-field-label">{html.escape(label)}</div><div class="pm-field-value">{html.escape(value)}</div>'
                for label, value in fields
            )
            citations = " ".join(idea.citations)
            st.markdown(
                f"""
                <div class="pm-idea">
                  <div class="pm-card-title">{index}. {html.escape(idea.title)}</div>
                  {field_html}
                  <div class="pm-field-label">Citations</div>
                  <div class="pm-citation">{html.escape(citations)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def evidence_dataframe(evidence: list[RetrievedEvidence]) -> pd.DataFrame:
    rows = []
    for item in evidence:
        rows.append(
            {
                "Evidence": item.evidence_id,
                "Paper": item.chunk.doc_id,
                "Title": item.chunk.doc_title,
                "Pages": (
                    str(item.chunk.page_start)
                    if item.chunk.page_start == item.chunk.page_end
                    else f"{item.chunk.page_start}-{item.chunk.page_end}"
                ),
                "Section": item.chunk.section,
                "Type": item.chunk.chunk_type,
                "Rerank": round(item.rerank_score, 4),
                "Hybrid": round(item.fusion_score, 4),
                "Selection": round(item.selection_score, 4),
            }
        )
    return pd.DataFrame(rows)


def render_evidence(evidence: list[RetrievedEvidence], retrieval_plan: Any) -> None:
    st.markdown("#### Retrieval plan")
    st.markdown(retrieval_plan.rationale)
    for query in retrieval_plan.queries:
        st.markdown(f"- `{query}`")
    st.markdown("#### Selected evidence")
    st.dataframe(evidence_dataframe(evidence), use_container_width=True, hide_index=True)
    for item in evidence:
        with st.expander(
            f"{item.evidence_id} · {item.chunk.doc_id} · {item.chunk.citation_label} · {item.chunk.section}"
        ):
            st.markdown(item.chunk.text)
            st.caption(
                f"Chunk {item.chunk.chunk_id} · type {item.chunk.chunk_type} · "
                f"rerank {item.rerank_score:.4f}"
            )


def render_evidence_path(result: Any) -> None:
    path = getattr(result, "evidence_path", [])
    if not path:
        st.info("No evidence-path summary was returned.")
        return
    for index, step in enumerate(path, start=1):
        st.markdown(f"**{index}.** {step}")
    st.caption("This is an inspectable workflow summary, not hidden chain-of-thought.")


def render_audit(audit: dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Citation coverage", f"{audit['citation_coverage'] * 100:.0f}%")
    col2.metric("Support rate", f"{audit['support_rate'] * 100:.0f}%")
    col3.metric("Evidence used", len(audit["evidence_used"]))
    col4.metric("Papers cited", audit["unique_sources"])
    if audit["unknown_ids"]:
        st.warning("Unknown evidence IDs: " + ", ".join(audit["unknown_ids"]))
    st.caption(f"Semantic citation audit: {audit['semantic_status']}")
    rows = [
        {
            "Claim": item.claim,
            "Citations": ", ".join(item.citations),
            "Verdict": item.verdict.replace("_", " "),
            "Explanation": item.explanation,
        }
        for item in audit["assessments"]
    ]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No auditable factual claims were returned.")


def serialize_analysis(
    mode: str,
    user_input: str,
    result: Any,
    retrieval_plan: Any,
    evidence: list[RetrievedEvidence],
    audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "project": "PaperMind: Citation-Grounded Research Reasoning and Idea Generation Assistant",
        "mode": mode,
        "request": user_input,
        "retrieval_plan": retrieval_plan.model_dump(),
        "result": result.model_dump(),
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "chunk": item.chunk.metadata(),
                "text": item.chunk.text,
                "scores": {
                    "dense": item.dense_score,
                    "lexical": item.lexical_score,
                    "fusion": item.fusion_score,
                    "rerank": item.rerank_score,
                    "selection": item.selection_score,
                },
            }
            for item in evidence
        ],
        "citation_audit": {
            key: (
                [item.model_dump() for item in value]
                if key == "assessments"
                else value
            )
            for key, value in audit.items()
        },
    }


def analysis_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PaperMind Analysis",
        "",
        f"**Mode:** {payload['mode']}",
        f"**Request:** {payload['request']}",
        "",
        "## Structured result",
        "",
        "```json",
        json.dumps(payload["result"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## Evidence",
    ]
    for item in payload["evidence"]:
        meta = item["chunk"]
        lines.extend(
            [
                "",
                f"### {item['evidence_id']} — {meta['doc_title']}",
                f"Source: {meta['citation_label']} · Section: {meta['section']}",
                "",
                item["text"],
            ]
        )
    return "\n".join(lines)
