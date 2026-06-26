# Getting started

> **Version:** 2026-06-26
> **Audience:** New contributors
> **Next:** [Project structure](./project-structure.md)

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10–3.12 | See `requires-python` in `pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | Recommended package manager |
| OpenSearch (Aiven) | Managed instance with k-NN + search pipelines |
| Hugging Face access | BGE and reranker models downloaded on first use |

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd disease-diagnosis-rag-system
uv sync
```

### 2. Configure environment

Copy the example file and fill in your OpenSearch credentials (never commit `.env`):

```bash
cp .env.example .env
```

Required variables:

```env
OPENSEARCH_HOST=your-aiven-host.aivencloud.com
OPENSEARCH_PORT=12345
OPENSEARCH_USERNAME=avnadmin
OPENSEARCH_PASSWORD=your-password
OPENSEARCH_TIMEOUT=60
```

Optional overrides (defaults are fine for local dev):

```env
RETRIEVE_INDEX_ALIAS=diseases
CURRENT_SEARCH_PIPELINE=hybrid-rrf
PATH_TO_MODELS=models
EMBEDDING_MODEL_REPO_ID=BAAI/bge-small-en-v1.5
EMBEDDING_MODEL=bge-small-en-v1.5
RERANKER_MODEL_REPO_ID=BAAI/bge-reranker-base
RERANKER_MODEL=bge-reranker-base
RETRIEVE_TOP_K=20
RERANK_TOP_K=5
INGEST_BATCH_SIZE=100
OPENSEARCH_POOL_MAXSIZE=16
```

`OPENSEARCH_TIMEOUT` — HTTP timeout in seconds for OpenSearch requests. Remote Aiven bulk ingest of 49 docs with embeddings often needs more than the library default (10s); increase to `120` if bulk writes still time out.

`OPENSEARCH_POOL_MAXSIZE` — urllib3 keep-alive pool size per host (default **16**). The sync client uses `Urllib3HttpConnection`; default pool size is **1**. If parallel eval or concurrent searches log `Connection pool is full`, raise this (and restart the kernel so the client singleton is recreated). Keep **`OPENSEARCH_POOL_MAXSIZE` ≥ parallel worker count** (e.g. `EXP02_WORKERS` in the live eval notebook).

### 3. Initialize OpenSearch

Bootstrap the search pipeline and DDXPlus index:

```bash
uv run python -m src.migrations.init_db upgrade
uv run python -m src.migrations.migrate_ddxplus_index upgrade
```

`init_db` creates the `hybrid-rrf` search pipeline and a bootstrap index. `migrate_ddxplus_index` creates `ddxplus_diseases` and points the `diseases` alias to it.

Rollback to the Symptom2Disease mapping:

```bash
uv run python -m src.migrations.migrate_ddxplus_index downgrade
```

See [DDXPlus index mapping](../ddxplus-index-mapping.md) for field schema and ingest steps.

### 4. Verify retrieval (after documents are indexed)

```python
from src.db.vector_db.opensearch import get_opensearch_client
from src.services.inference.embeddings.service import TextEmbeddingService
from src.services.rag import Retriever
from src.services.rag.preprocess import PreprocessPipeline
from src.services.rag.schemas import HybridRetrieveRequest

retriever = Retriever(
    client=get_opensearch_client(),
    embed_service=TextEmbeddingService(),
    preprocess=PreprocessPipeline(),
)
result = retriever.search_hybrid(HybridRetrieveRequest(query="fever cough fatigue"))
print(result.hits)
```

Compare BM25 vs k-NN vs hybrid:

```python
from src.services.rag.schemas import RetrievalMode, RetrieveExperimentRequest

comparison = retriever.run_experiment(
    RetrieveExperimentRequest(query="fever cough fatigue")
)
print(comparison.modes_run)  # ["bm25", "knn", "hybrid"]

hybrid_hits = comparison.results[RetrievalMode.HYBRID].hits
print(hybrid_hits)
```

Production path (hybrid retrieve top 20 → cross-encoder rerank top 5):

```python
from src.services.rag import RAGService

rag = RAGService()
result = rag.query("fever cough fatigue")
print(result.hits)  # scores are cross-encoder scores after rerank
```

Batch ingest (normalize symptoms, embed `embed_text`, bulk upsert):

```python
import json
from pathlib import Path

from src.services.rag import RAGService
from src.services.rag.schemas import DiseaseDocument

kb = json.loads(Path("data/kb/kb_ddxplus.json").read_text())
records = [DiseaseDocument.model_validate(doc) for doc in kb]
rag = RAGService()
print(rag.ingest(records))  # 49
```

Interactive walkthrough: [`notebooks/walkthrough.ipynb`](../../notebooks/walkthrough.ipynb) (run `uv sync --extra dev`).

Live EXP-02 eval against OpenSearch: [`notebooks/exp02_live_eval.ipynb`](../../notebooks/exp02_live_eval.ipynb) (requires DDXPlus eval data under `data/eval/`). Tunables: `EXP02_SAMPLE`, `EXP02_WORKERS`, `EXP02_REINGEST`, `EXP02_RUN_EVAL`, `EXP02_RESULTS`, `OPENSEARCH_POOL_MAXSIZE`. Committed metrics: [`experiments/exp02/results/live_eval_latest.json`](../../experiments/exp02/results/live_eval_latest.json).

### 5. Run tests (before commit)

```bash
uv sync --extra dev
uv run pytest tests/rag
```

Tests mock OpenSearch, BGE, and reranker — no `.env` or indexed documents required. See [README](../../README.md#testing-before-commit) for pre-commit hooks.

## First-day checklist

- [ ] Read [Project structure](./project-structure.md)
- [ ] Read [Development philosophy](./development-philosophy.md)
- [ ] Copy `.env` and run migrations
- [ ] Run one retrieval experiment against the `diseases` alias
- [ ] Run `uv run pytest tests/rag`

## Common issues

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| `resource_already_exists_exception` on upgrade | Index already exists | Run `downgrade` first, or skip if intentional |
| DNS / connection errors to OpenSearch | Wrong host or network | Check Aiven dashboard and `.env` |
| Model download on every import | First run or missing `models/` | Wait for `snapshot_download`; ensure `models/` is writable (BGE + reranker) |
| Hybrid search returns empty | No documents indexed yet | Run `RAGService.ingest()` or see [DDXPlus index mapping](../ddxplus-index-mapping.md) |
| Bulk ingest `TimeoutError` / write timed out | Default HTTP timeout too low for remote cluster | Set `OPENSEARCH_TIMEOUT=120` in `.env` and restart the kernel |
| `Connection pool is full` (urllib3) during parallel eval | Default urllib3 pool size is 1; too many concurrent searches | Set `OPENSEARCH_POOL_MAXSIZE=16` (≥ `EXP02_WORKERS`); restart kernel |
| BM25 on `symptoms` field fails | `symptoms` is `keyword`, not `text` | Use `keyword_text` for BM25 |

## Changelog

| Date | Change |
|------|--------|
| 2026-06-26 | Documented EXP-02 save/load (`EXP02_RUN_EVAL`, `EXP02_RESULTS`, `live_eval_latest.json`) |
| 2026-06-25 | Documented `OPENSEARCH_POOL_MAXSIZE`, parallel eval tuning, urllib3 pool troubleshooting |
| 2026-06-25 | Documented `PreprocessPipeline` on `Retriever`, ingest example, `OPENSEARCH_TIMEOUT`, EXP-02 notebook |
| 2026-06-22 | Fixed `Retriever` examples to pass required OpenSearch `client` |
| 2026-06-20 | Added reranker settings, `RAGService.query()` example, reranker in test note |
| 2026-06-17 | Added test commands; `RetrievalMode` experiment result keys |
| 2026-06-11 | Fixed Retriever import; aligned setup with `.env.example` |
| 2026-06-11 | Removed duplicate project description; streamlined setup instructions |
| 2026-06-09 | Initial getting started guide |
