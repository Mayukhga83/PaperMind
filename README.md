---
title: PaperMind
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# PaperMind

**Citation-Grounded Research Reasoning and Idea Generation Assistant**

Developed by **Mayukh Das**, TU Braunschweig  
Email: **mayukh@ifis.cs.tu-bs.de**

PaperMind is a quality-first research intelligence application for one to five scientific PDFs. It treats retrieved passages as evidence rather than generic prompt context, then exposes the evidence selection and citation audit behind each result.

## What PaperMind does

- Answers focused research questions with evidence identifiers.
- Verifies whether a claim is supported, qualified, contradicted, or not established by the uploaded corpus.
- Extracts grounded dataset, evaluation, method, reasoning, deployment, safety, and theoretical gaps.
- Generates context-dependent research ideas with technical approaches and evaluation plans.
- Shows the multi-query retrieval plan, selected passages, reranking scores, evidence path, and sentence-level citation support audit.
- Exports complete analyses as JSON or Markdown.
- Limits the public demo to 15 valid analysis launches per browser session.

## Fixed quality-first stack

| Layer | Technology |
|---|---|
| Interface | Streamlit |
| PDF extraction | PyMuPDF |
| Text processing | Page-aware cleaning, section detection, paragraph-aware token chunking |
| Embeddings | `text-embedding-3-large` |
| Vector index | Chroma with cosine HNSW |
| Lexical retrieval | BM25 |
| Retrieval | Task-specific multi-query hybrid retrieval with reciprocal-rank fusion |
| Reranking | `BAAI/bge-reranker-v2-m3` |
| Evidence selection | Relevance plus source/section diversity and redundancy control |
| Reasoning | `gpt-5.4` with structured outputs |
| API compatibility | Structured output calls deliberately omit the optional `reasoning.effort` request parameter |
| Citation validation | Deterministic coverage checks plus LLM-based claim/evidence support audit |
| Hosted deployment | Docker-based Hugging Face Space |

There is no visible model selector or API-key field. The application uses one fixed high-quality pipeline.

## Local VS Code setup

### 1. Requirements

Use **Python 3.11**. It is also the Python version used by the supplied Dockerfile.

Check installed Python versions on Windows:

```powershell
py -0p
```

### 2. Create and activate a virtual environment

Open the extracted `papermind` folder in VS Code, then run:

```powershell
py -3.11 -m venv venv
venv\Scripts\activate
```

If PowerShell prevents activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\activate
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

The BGE reranker model is downloaded from Hugging Face the first time an analysis reaches the reranking stage. It is then reused from the local model cache.

### 4. Configure the hidden OpenAI key

Copy the example file:

```powershell
copy .env.example .env
```

Edit `.env` and set:

```dotenv
OPENAI_API_KEY=your_real_key_here
```

Keep `.env` local. It is already excluded by `.gitignore`.

The fixed defaults are:

```dotenv
OPENAI_CHAT_MODEL=gpt-5.4
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

### 5. Start PaperMind

```powershell
streamlit run app.py
```

Open the local URL shown in the terminal, normally `http://localhost:7860`.

## Recommended first check

1. Upload one text-based research PDF.
2. Select **Build Research Index**.
3. Start with **Ask with Citations** and ask:  
   `What are the paper's central findings and explicitly stated limitations?`
4. Inspect **Evidence** to confirm page numbers and passages.
5. Inspect **Citation Audit** to see claim-level support judgments.
6. Test **Verify Claim**, **Extract Research Gaps**, and **Generate Ideas**.
7. Add a second paper and confirm the Evidence tab selects passages across papers when relevant.

Scanned image-only PDFs are not supported in this version because OCR is intentionally not included.

## Architecture

```text
PDFs
  -> page-aware extraction and repeated header/footer cleaning
  -> section-aware paragraph chunking with rich metadata
  -> OpenAI large embeddings + Chroma cosine index
  -> task-specific query expansion
  -> dense retrieval + BM25 retrieval
  -> reciprocal-rank fusion and metadata priors
  -> BGE cross-encoder reranking
  -> diversity-aware evidence selection
  -> structured GPT reasoning
  -> deterministic and semantic citation audit
  -> Streamlit evidence, audit, and export views
```

## Privacy model

- Every Streamlit browser session receives a separate temporary runtime directory and Chroma collection.
- Uploaded files are not intended to be committed or permanently retained.
- Expired session directories are removed according to `SESSION_TTL_HOURS`.
- Do not use the public demo for confidential files or documents you are not permitted to process.

## Public demo safeguards

- A browser session can launch at most **15 analyses** across all four research tasks.
- Uploading papers, building or rebuilding an index, changing tasks, viewing results, and exporting files do not consume attempts.
- A valid analysis consumes one attempt immediately before the OpenAI-backed pipeline begins. If a later model, retrieval, or citation-audit step fails, the attempt remains consumed because API work may already have started.
- Clearing the document index does not reset the allowance. The counter resets only when Streamlit creates a genuinely new browser session.
- This is a lightweight cost-control measure, not strong anti-abuse protection; a determined visitor can create another browser session.

The limit is configured with:

```dotenv
MAX_ANALYSES_PER_SESSION=15
```

## Tests

Install development dependencies and run:

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
ruff check .
python -m compileall -q .
```

## Docker test

```bash
docker build -t papermind .
docker run --rm -p 7860:7860 --env-file .env papermind
```

Then open `http://localhost:7860`.

## Hugging Face Spaces deployment readiness

The repository is configured for a **Docker SDK Hugging Face Space**:

- The README front matter declares `sdk: docker` and `app_port: 7860`.
- The Docker container launches Streamlit on `0.0.0.0:7860`.
- `.streamlit/config.toml` also sets address `0.0.0.0`, port `7860`, and a 25 MB upload limit.
- XSRF protection is disabled in both the Streamlit configuration and Docker launch command to avoid file-uploader `403` responses behind the Hugging Face proxy/iframe.
- Store `OPENAI_API_KEY` in **Space Settings → Variables and secrets → New secret**. Never commit `.env` or `.streamlit/secrets.toml`.
- The recommended hosted hardware for the full BGE reranker pipeline is Hugging Face **CPU Upgrade**.

After changing deployment-related files, upload the project root again and wait for the Space to rebuild. The uploaded root must directly contain `app.py`, `Dockerfile`, `README.md`, `requirements.txt`, and `src/`.

From that project root, a direct update can be uploaded with:

```powershell
hf upload YOUR_USERNAME/papermind . . --repo-type=space --commit-message "Update PaperMind"
```

After the build finishes, hard-refresh the Space before retesting PDF upload.
