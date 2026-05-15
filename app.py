from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

from src.config import (
    cleanup_expired_sessions,
    clear_session,
    load_config,
    session_paths,
)
from src.evaluation.citation_checker import citation_audit
from src.ingestion.chunker import chunk_pages
from src.ingestion.pdf_loader import extract_pdf
from src.reasoning.claim_verifier import verify_claim
from src.reasoning.gap_extractor import extract_gaps
from src.reasoning.idea_generator import generate_ideas
from src.reasoning.llm_client import OpenAIReasoner
from src.reasoning.qa import answer_question
from src.retrieval.embeddings import OpenAIEmbedder
from src.retrieval.multi_query import generate_retrieval_plan
from src.retrieval.retriever import HybridRetriever
from src.retrieval.vector_store import PaperVectorStore
from src.schemas.domain import DocumentSummary
from src.ui.components import (
    analysis_markdown,
    render_audit,
    render_author_card,
    render_document_cards,
    render_evidence,
    render_evidence_path,
    render_how_it_works,
    render_header,
    render_result,
    render_session_usage,
    serialize_analysis,
)
from src.ui.styles import APP_CSS

st.set_page_config(
    page_title="PaperMind",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(APP_CSS, unsafe_allow_html=True)

CONFIG = load_config()


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "session_id": uuid.uuid4().hex,
        "documents": [],
        "index_ready": False,
        "corpus_fingerprint": "",
        "analysis": None,
        "analysis_attempts_used": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()
SESSION_ID = st.session_state.session_id
PATHS = session_paths(CONFIG, SESSION_ID)
cleanup_expired_sessions(CONFIG, active_session_id=SESSION_ID)


def corpus_fingerprint(files: list[Any]) -> str:
    digest = hashlib.sha256()
    for uploaded in files:
        payload = uploaded.getvalue()
        digest.update(uploaded.name.encode("utf-8", errors="ignore"))
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def validate_uploads(files: list[Any]) -> None:
    if not files:
        raise ValueError("Upload at least one PDF before building the research index.")
    if len(files) > CONFIG.max_papers:
        raise ValueError(f"Upload at most {CONFIG.max_papers} PDFs for this demo.")
    max_bytes = CONFIG.max_pdf_mb * 1024 * 1024
    for uploaded in files:
        payload = uploaded.getvalue()
        if not uploaded.name.lower().endswith(".pdf"):
            raise ValueError(f"{uploaded.name} is not a PDF file.")
        if len(payload) > max_bytes:
            raise ValueError(
                f"{uploaded.name} exceeds the {CONFIG.max_pdf_mb} MB per-file limit."
            )
        if not payload.startswith(b"%PDF-"):
            raise ValueError(f"{uploaded.name} does not appear to be a valid PDF.")


def build_index(files: list[Any]) -> None:
    if not CONFIG.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY was not found. Add it to the local .env file before indexing."
        )
    validate_uploads(files)
    clear_session(CONFIG, SESSION_ID)
    paths = session_paths(CONFIG, SESSION_ID)
    all_chunks = []
    summaries: list[DocumentSummary] = []

    progress = st.progress(0, text="Preparing research corpus...")
    total_steps = max(1, len(files) + 2)
    for index, uploaded in enumerate(files, start=1):
        payload = uploaded.getvalue()
        safe_name = Path(uploaded.name).name
        destination = paths["uploads"] / safe_name
        destination.write_bytes(payload)
        doc_id = f"P{index}"
        progress.progress(
            index / total_steps,
            text=f"Extracting and structuring {safe_name}...",
        )
        title, pages = extract_pdf(payload, doc_id=doc_id, file_name=safe_name)
        chunks = chunk_pages(
            pages,
            target_tokens=CONFIG.chunk_target_tokens,
            overlap_tokens=CONFIG.chunk_overlap_tokens,
        )
        if not chunks:
            raise ValueError(f"No usable evidence chunks were produced from {safe_name}.")
        all_chunks.extend(chunks)
        summaries.append(
            DocumentSummary(
                doc_id=doc_id,
                title=title,
                file_name=safe_name,
                pages=max(page.page_number for page in pages),
                chunks=len(chunks),
            )
        )

    progress.progress(
        (len(files) + 1) / total_steps,
        text=f"Embedding {len(all_chunks)} evidence chunks...",
    )
    embedder = OpenAIEmbedder(CONFIG.openai_api_key, CONFIG.embedding_model)
    embeddings = embedder.embed_documents([chunk.text for chunk in all_chunks])
    store = PaperVectorStore(paths["chroma"])
    store.reset()
    store.add(all_chunks, embeddings)
    progress.progress(1.0, text="Research index ready.")

    st.session_state.documents = summaries
    st.session_state.index_ready = True
    st.session_state.corpus_fingerprint = corpus_fingerprint(files)
    st.session_state.analysis = None


def run_analysis(mode: str, request: str) -> dict[str, Any]:
    if not CONFIG.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")
    if not st.session_state.index_ready:
        raise ValueError("Build the research index before running an analysis.")
    if not request.strip():
        raise ValueError("Enter a focused question, claim, or analysis instruction.")

    reasoner = OpenAIReasoner(CONFIG.openai_api_key, CONFIG.chat_model)
    embedder = OpenAIEmbedder(CONFIG.openai_api_key, CONFIG.embedding_model)
    store = PaperVectorStore(PATHS["chroma"])
    if store.count() == 0:
        raise ValueError("The current research index is empty. Rebuild the index.")

    plan = generate_retrieval_plan(
        reasoner,
        mode,
        request,
        CONFIG.query_count,
    )
    retriever = HybridRetriever(CONFIG, store, embedder)
    evidence = retriever.retrieve(mode, request, plan)
    if not evidence:
        raise ValueError("No relevant evidence was retrieved from the uploaded papers.")

    if mode == "Ask with Citations":
        result = answer_question(reasoner, request, evidence)
    elif mode == "Verify Claim":
        result = verify_claim(reasoner, request, evidence)
    elif mode == "Extract Research Gaps":
        result = extract_gaps(reasoner, request, evidence)
    elif mode == "Generate Ideas":
        result = generate_ideas(reasoner, request, evidence)
    else:
        raise ValueError(f"Unsupported analysis mode: {mode}")

    audit = citation_audit(
        result,
        evidence,
        reasoner,
        limit=CONFIG.citation_check_limit,
    )
    payload = serialize_analysis(mode, request, result, plan, evidence, audit)
    return {
        "mode": mode,
        "request": request,
        "plan": plan,
        "evidence": evidence,
        "result": result,
        "audit": audit,
        "payload": payload,
    }


with st.sidebar:
    st.markdown("### PaperMind status")
    st.caption("One fixed, quality-first research pipeline")
    if CONFIG.openai_api_key:
        st.success("OpenAI configuration detected")
    else:
        st.error("OpenAI key not configured")
    st.metric("Indexed papers", len(st.session_state.documents))
    st.metric("Paper limit", CONFIG.max_papers)
    st.metric(
        "Analyses remaining",
        max(
            0,
            CONFIG.max_analyses_per_session
            - st.session_state.analysis_attempts_used,
        ),
    )
    st.write("**Research index:**", "Ready" if st.session_state.index_ready else "Not built")
    st.divider()
    if st.button("Clear current session", use_container_width=True):
        clear_session(CONFIG, SESSION_ID)
        st.session_state.documents = []
        st.session_state.index_ready = False
        st.session_state.corpus_fingerprint = ""
        st.session_state.analysis = None
        st.rerun()

render_header()
render_author_card()
render_how_it_works(CONFIG.max_analyses_per_session)

st.markdown('<div class="pm-section-title">1. Upload research papers</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="pm-section-copy">Upload one to {CONFIG.max_papers} text-based PDFs. Each file may be up to {CONFIG.max_pdf_mb} MB.</div>',
    unsafe_allow_html=True,
)
uploaded_files = st.file_uploader(
    "Research PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded_files and len(uploaded_files) > CONFIG.max_papers:
    st.error(f"Please keep the selection to at most {CONFIG.max_papers} PDFs.")

current_fingerprint = corpus_fingerprint(uploaded_files) if uploaded_files else ""
if (
    st.session_state.index_ready
    and current_fingerprint
    and current_fingerprint != st.session_state.corpus_fingerprint
):
    st.warning("The selected papers changed. Rebuild the research index before analysis.")

build_disabled = not uploaded_files or len(uploaded_files) > CONFIG.max_papers
if st.button(
    "Build Research Index",
    type="primary",
    disabled=build_disabled,
    use_container_width=True,
):
    try:
        with st.status("Building the high-quality research index", expanded=True) as status:
            st.write("Extracting page-aware text and detecting document structure...")
            build_index(uploaded_files)
            status.update(label="Research index built successfully", state="complete")
        st.success("PaperMind is ready for citation-grounded analysis.")
    except Exception as exc:
        st.session_state.index_ready = False
        st.error("The research index could not be built.")
        with st.expander("Technical detail"):
            st.code(str(exc))

render_document_cards(st.session_state.documents)

st.markdown('<div class="pm-section-title">2. Choose a research task</div>', unsafe_allow_html=True)
mode = st.radio(
    "Analysis mode",
    [
        "Ask with Citations",
        "Verify Claim",
        "Extract Research Gaps",
        "Generate Ideas",
    ],
    horizontal=True,
    label_visibility="collapsed",
)
mode_help = {
    "Ask with Citations": "Ask a focused question and receive an evidence-grounded synthesis.",
    "Verify Claim": "Test whether the uploaded papers support, qualify, contradict, or cannot establish a claim.",
    "Extract Research Gaps": "Identify grounded limitations, open problems, and technically actionable research directions.",
    "Generate Ideas": "Generate context-dependent research ideas grounded in the uploaded corpus.",
}
st.caption(mode_help[mode])

render_session_usage(
    st.session_state.analysis_attempts_used,
    CONFIG.max_analyses_per_session,
)

placeholders = {
    "Ask with Citations": "What are the central findings and limitations relevant to contextual model evaluation?",
    "Verify Claim": "Longer context consistently improves toxicity classification across settings.",
    "Extract Research Gaps": "Identify the most important unresolved evaluation and methodological gaps across these papers.",
    "Generate Ideas": "Generate research ideas at the intersection of the papers' limitations, methods, and findings.",
}
request = st.text_area(
    "Research question or instruction",
    placeholder=placeholders[mode],
    height=125,
    key=f"analysis_request_{mode}",
)

# Streamlit text areas submit their latest browser value when another widget is
# activated. Disabling the button from the current text value can therefore
# require a misleading first click merely to synchronize the text. Keep the
# action available whenever the corpus is ready, and validate empty input after
# the click instead.
analysis_limit_reached = (
    st.session_state.analysis_attempts_used >= CONFIG.max_analyses_per_session
)
analysis_disabled = (
    not st.session_state.index_ready
    or not CONFIG.openai_api_key
    or analysis_limit_reached
    or (
        current_fingerprint
        and current_fingerprint != st.session_state.corpus_fingerprint
    )
)
run_clicked = st.button(
    "Run Citation-Grounded Analysis",
    type="primary",
    disabled=analysis_disabled,
    use_container_width=True,
)
if run_clicked:
    if not request.strip():
        st.warning("Enter a focused question, claim, or analysis instruction first.")
    else:
        try:
            # Validate local prerequisites before consuming an attempt. Once the
            # OpenAI-backed pipeline is launched, the attempt remains consumed
            # even if a later retrieval, generation, or audit step fails.
            if not CONFIG.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not configured.")
            store = PaperVectorStore(PATHS["chroma"])
            if store.count() == 0:
                raise ValueError("The current research index is empty. Rebuild the index.")

            st.session_state.analysis_attempts_used += 1
            with st.status("Running PaperMind's evidence pipeline", expanded=True) as status:
                st.write("Generating complementary retrieval queries...")
                st.write("Running hybrid retrieval, BGE reranking, and diversity selection...")
                st.write("Reasoning over the selected evidence and auditing citations...")
                st.session_state.analysis = run_analysis(mode, request)
                status.update(label="Analysis complete", state="complete")
        except Exception as exc:
            st.error("PaperMind could not complete this analysis.")
            with st.expander("Technical detail"):
                st.code(str(exc))

analysis = st.session_state.analysis
if analysis:
    st.markdown('<div class="pm-section-title">3. Inspect the analysis</div>', unsafe_allow_html=True)
    result_tab, evidence_tab, path_tab, audit_tab, export_tab = st.tabs(
        ["Result", "Evidence", "Evidence Path", "Citation Audit", "Export"]
    )
    with result_tab:
        render_result(analysis["result"])
    with evidence_tab:
        render_evidence(analysis["evidence"], analysis["plan"])
    with path_tab:
        render_evidence_path(analysis["result"])
    with audit_tab:
        render_audit(analysis["audit"])
    with export_tab:
        json_text = json.dumps(
            analysis["payload"], indent=2, ensure_ascii=False
        )
        markdown_text = analysis_markdown(analysis["payload"])
        left, right = st.columns(2)
        with left:
            st.download_button(
                "Download JSON",
                data=json_text,
                file_name="papermind_analysis.json",
                mime="application/json",
                use_container_width=True,
            )
        with right:
            st.download_button(
                "Download Markdown",
                data=markdown_text,
                file_name="papermind_analysis.md",
                mime="text/markdown",
                use_container_width=True,
            )

st.markdown(
    """
    <div class="pm-footer">
      PaperMind · Citation-Grounded Research Reasoning and Idea Generation Assistant
    </div>
    """,
    unsafe_allow_html=True,
)
