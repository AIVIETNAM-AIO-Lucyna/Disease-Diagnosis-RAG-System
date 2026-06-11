# Getting started

> **Version:** 2026-06-11  
> **Audience:** New contributors  
> **Next:** [Project structure](./project-structure.md)

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10–3.12 | See `requires-python` in `pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | Recommended package manager |
| OpenSearch (Aiven) | Managed instance with k-NN + search pipelines |
| Hugging Face access | BGE model downloaded on first settings load |

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
```

Optional overrides (defaults are fine for local dev):

```env
RETRIEVE_INDEX_ALIAS=diseases
CURRENT_SEARCH_PIPELINE=hybrid-rrf
PATH_TO_MODELS=models
EMBEDDING_MODEL_REPO_ID=BAAI/bge-small-en-v1.5
EMBEDDING_MODEL=bge-small-en-v1.5
```

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
from src.services.ai_inference.bge.service import BGEInferenceService
from src.services.rag import Retriever
from src.services.rag.schemas import HybridRetrieveRequest

retriever = Retriever(embed_service=BGEInferenceService())
result = retriever.search_hybrid(HybridRetrieveRequest(query="fever cough fatigue"))
print(result.hits)
```

Compare BM25 vs k-NN vs hybrid:

```python
from src.services.rag.schemas import RetrieveExperimentRequest

comparison = retriever.run_experiment(
    RetrieveExperimentRequest(query="fever cough fatigue")
)
print(comparison.modes_run)
```

Interactive walkthrough: [`notebooks/example.ipynb`](../../notebooks/example.ipynb) (run `uv sync --extra dev`).

## First-day checklist

- [ ] Read [Project structure](./project-structure.md)
- [ ] Read [Development philosophy](./development-philosophy.md)
- [ ] Copy `.env` and run migrations
- [ ] Run one retrieval experiment against the `diseases` alias

## Common issues

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| `resource_already_exists_exception` on upgrade | Index already exists | Run `downgrade` first, or skip if intentional |
| DNS / connection errors to OpenSearch | Wrong host or network | Check Aiven dashboard and `.env` |
| Model download on every import | First run or missing `models/` | Wait for `snapshot_download`; ensure `models/` is writable |
| Hybrid search returns empty | No documents indexed yet | Implement/run ingestion (see [Roadmap](./roadmap-and-refactors.md)) |
| BM25 on `symptoms` field fails | `symptoms` is `keyword`, not `text` | Use `keyword_text` for BM25 |

## Changelog

| Date | Change |
|------|--------|
| 2026-06-11 | Fixed Retriever import; aligned setup with `.env.example` |
| 2026-06-11 | Removed duplicate project description; streamlined setup instructions |
| 2026-06-09 | Initial getting started guide |
