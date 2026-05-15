from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str
    chat_model: str
    embedding_model: str
    reranker_model: str
    data_dir: Path
    max_papers: int = 5
    max_pdf_mb: int = 25
    chunk_target_tokens: int = 900
    chunk_overlap_tokens: int = 170
    dense_results_per_query: int = 22
    lexical_results: int = 35
    candidate_limit: int = 70
    final_evidence_count: int = 10
    query_count: int = 5
    citation_check_limit: int = 24
    session_ttl_hours: int = 6
    max_analyses_per_session: int = 15


def _streamlit_secret(name: str) -> Any | None:
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


def _get_setting(name: str, default: str = "") -> str:
    secret = _streamlit_secret(name)
    if secret not in (None, ""):
        return str(secret)
    return os.getenv(name, default)


def load_config() -> AppConfig:
    data_dir = Path(_get_setting("PAPERMIND_DATA_DIR", "data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return AppConfig(
        openai_api_key=_get_setting("OPENAI_API_KEY"),
        chat_model=_get_setting("OPENAI_CHAT_MODEL", "gpt-5.4"),
        embedding_model=_get_setting(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"
        ),
        reranker_model=_get_setting(
            "RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
        ),
        data_dir=data_dir,
        max_papers=int(_get_setting("MAX_PAPERS", "5")),
        max_pdf_mb=int(_get_setting("MAX_PDF_MB", "25")),
        chunk_target_tokens=int(_get_setting("CHUNK_TARGET_TOKENS", "900")),
        chunk_overlap_tokens=int(_get_setting("CHUNK_OVERLAP_TOKENS", "170")),
        dense_results_per_query=int(
            _get_setting("DENSE_RESULTS_PER_QUERY", "22")
        ),
        lexical_results=int(_get_setting("LEXICAL_RESULTS", "35")),
        candidate_limit=int(_get_setting("CANDIDATE_LIMIT", "70")),
        final_evidence_count=int(_get_setting("FINAL_EVIDENCE_COUNT", "10")),
        query_count=int(_get_setting("QUERY_COUNT", "5")),
        citation_check_limit=int(_get_setting("CITATION_CHECK_LIMIT", "24")),
        session_ttl_hours=int(_get_setting("SESSION_TTL_HOURS", "6")),
        max_analyses_per_session=int(
            _get_setting("MAX_ANALYSES_PER_SESSION", "15")
        ),
    )


def session_paths(config: AppConfig, session_id: str) -> dict[str, Path]:
    root = config.data_dir / "runtime" / session_id
    paths = {
        "root": root,
        "uploads": root / "uploads",
        "chroma": root / "chroma",
        "exports": root / "exports",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    (root / ".last_access").touch()
    return paths


def clear_session(config: AppConfig, session_id: str) -> None:
    root = config.data_dir / "runtime" / session_id
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def cleanup_expired_sessions(config: AppConfig, active_session_id: str = "") -> None:
    runtime = config.data_dir / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - (config.session_ttl_hours * 3600)
    for child in runtime.iterdir():
        if not child.is_dir() or child.name == active_session_id:
            continue
        marker = child / ".last_access"
        timestamp = marker.stat().st_mtime if marker.exists() else child.stat().st_mtime
        if timestamp < cutoff:
            shutil.rmtree(child, ignore_errors=True)
