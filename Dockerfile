FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/user/.cache/huggingface \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8 \
    PAPERMIND_DATA_DIR=/home/user/app/data

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 \
    && python -m pip install -r requirements.txt

# Cache the fixed reranker during image build so the first visitor does not trigger a model download.
RUN python - <<'PY'
from transformers import AutoModelForSequenceClassification, AutoTokenizer
model_name = "BAAI/bge-reranker-v2-m3"
AutoTokenizer.from_pretrained(model_name)
AutoModelForSequenceClassification.from_pretrained(model_name)
print(f"Cached {model_name}")
PY

COPY --chown=user:user . /home/user/app
RUN mkdir -p /home/user/app/data/runtime /home/user/app/data/exports \
    && chown -R user:user /home/user/app /home/user/.cache

USER user
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl --fail http://localhost:7860/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=7860", "--server.headless=true", "--server.enableXsrfProtection=false", "--server.maxUploadSize=25"]
