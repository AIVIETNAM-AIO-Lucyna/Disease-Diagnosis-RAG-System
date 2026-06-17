# Project structure

> **Version:** 2026-06-17
> **See also:** [Development philosophy](./development-philosophy.md), [Roadmap](./roadmap-and-refactors.md)

## Repository layout

```
disease-diagnosis-rag-system/
├── docs/                          # Contributor documentation (you are here)
├── indices/
│   └── diseases/
│       ├── init_mapping.json          # Symptom2Disease mapping (bootstrap)
│       └── ddxplus_mapping.json       # DDXPlus mapping (active)
├── models/                        # Downloaded HF models (gitignored)
├── src/
│   ├── settings.py                # Env-based config (OpenSearch, models, retrieval)
│   ├── db/
│   │   └── vector_db/
│   │       ├── base.py            # VectorDB protocol
│   │       └── opensearch.py      # Sync OpenSearch client
│   ├── schemas/                   # OpenSearch wire/response models (shared infra)
│   │   ├── base.py                # RWSBaseModel, ORSBaseModel
│   │   ├── opensearch_responses.py
│   │   └── search_pipelines.py
│   ├── migrations/
│   │   ├── init_db.py             # Index + alias + search pipeline bootstrap
│   │   └── migrate_ddxplus_index.py
│   └── services/
│       ├── ai_inference/
│       │   └── bge/
│       │       └── service.py     # BGE query embedding
│       └── rag/
│           ├── preprocess.py      # Query normalization + synonyms
│           ├── ingest.py          # Document views + bulk upsert (stub)
│           ├── retrieve.py        # Retriever (BM25 / k-NN / hybrid)
│           ├── pipeline.py        # RAGService orchestration
│           └── schemas.py         # Retrieval request/response DTOs
├── pyproject.toml
├── tests/                         # pytest suite (mocked OpenSearch + BGE)
│   ├── conftest.py
│   └── rag/
│       ├── conftest.py
│       └── retrieve.py            # Retriever unit tests
├── notebooks/
│   └── example.ipynb              # Retrieval walkthrough (BM25 / k-NN / hybrid)
├── README.md
└── .env                           # Local secrets (not in git)
```

## Layer responsibilities

```mermaid
flowchart TD
    subgraph app [Application layer]
        RAG[RAGService / future API]
        BGE[BGEInferenceService]
    end

    subgraph services [Service layer]
        Retriever[Retriever]
        RSchemas[rag/schemas.py]
    end

    subgraph infra [Infrastructure layer]
        OS[OpenSearchClient]
        OSchemas[schemas/ OpenSearch DTOs]
        Settings[settings.py]
    end

    subgraph external [External]
        Aiven[(OpenSearch Aiven)]
        HF[(Hugging Face models)]
    end

    RAG --> Retriever
    Retriever --> BGE
    Retriever --> OS
    Retriever --> RSchemas
    OS --> OSchemas
    OS --> Aiven
    BGE --> HF
    Settings --> OS
    Settings --> BGE
```

| Layer | Path | Responsibility |
|-------|------|----------------|
| **Settings** | `src/settings.py` | Secrets, paths, retrieval defaults, model download |
| **DB / vector store** | `src/db/vector_db/` | Thin OpenSearch client; no business logic |
| **OpenSearch schemas** | `src/schemas/` | Parse/serialize OpenSearch API bodies (RWS / ORS) |
| **RAG schemas** | `src/services/rag/schemas.py` | Retrieval requests, slim `RetrieveResult`, experiment DTOs |
| **AI inference** | `src/services/ai_inference/` | Model loading and embedding (BGE today; reranker later) |
| **RAG service** | `src/services/rag/` | Retrieval orchestration, future ingest/rerank/generate |
| **Migrations** | `src/migrations/` | Idempotent index/pipeline setup scripts |
| **Index definitions** | `indices/` | JSON mappings versioned in git |

## Key modules

### `src/db/vector_db/opensearch.py`

- **`OpenSearchClient`** — sync; used by migrations, scripts, notebooks, and services
- FastAPI routes offload blocking work with `asyncio.to_thread` at the service boundary
- Methods: index CRUD, aliases, search pipelines, `query()`, `bulk()`

### `src/schemas/` (OpenSearch infrastructure)

| Model base | Direction | Method |
|------------|-----------|--------|
| `RWSBaseModel` | App → OpenSearch | `to_dict()` |
| `ORSBaseModel` | OpenSearch → App | `from_opensearch()` |

Used for search pipeline bodies, mapping responses, and raw search responses.

### `src/services/rag/schemas.py`

Domain-specific retrieval DTOs:

- **Requests:** `Bm25RetrieveRequest`, `VectorRetrieveRequest`, `HybridRetrieveRequest` — each builds OpenSearch Query DSL via `to_search_body()`. Vector/hybrid requests carry an optional `embedding`; the retriever sets it before calling `to_search_body()`.
- **Experiment request:** `RetrieveExperimentRequest` — shared query, optional fixed `embedding`, `modes` list
- **Production response:** `RetrieveResult` — `hits` + optional `took_ms`
- **Experiment response:** `ExperimentCompareResponse` — `results: dict[RetrievalMode, ExperimentModeResult]` plus `modes_run` helper
- **Internal:** `SearchExecution`, `PreprocessableRequest` TypeVar — used by `Retriever` execute helpers

### `src/services/rag/` modules

| Module | Status | Owner |
|--------|--------|-------|
| `schemas.py` | Done | Retrieval — request/response DTOs |
| `preprocess.py` | Done | Retrieval — query normalization + synonyms |
| `retrieve.py` | Done | Retrieval — BM25, k-NN, hybrid, `run_experiment()` |
| `pipeline.py` | Partial | Retrieval — `RAGService.query()` only |
| `ingest.py` | Stub | Data team — `DiseaseDocument`, `BulkIngestRequest` |

### Index mappings (`indices/diseases/`)

Two mapping files versioned in git. Retrieval always queries the `diseases` **alias**.

| Mapping file | Physical index | Dataset |
|--------------|----------------|---------|
| `init_mapping.json` | `init_diseases` | Symptom2Disease (24 disease classes) |
| `ddxplus_mapping.json` | `ddxplus_diseases` | DDXPlus (49 pathologies) — **active** |

See [DDXPlus index mapping](../ddxplus-index-mapping.md) for full field reference.

## Data flow: retrieval

1. Caller builds a `HybridRetrieveRequest` (or BM25 / vector variant)
2. `Retriever` optionally preprocesses the query (`preprocess.py`)
3. For vector/hybrid: `Retriever` sets `request.embedding` (caller-supplied or `BGEInferenceService.embed_query()` with the BGE search prefix)
4. Request schema builds OpenSearch Query DSL via `to_search_body()`
5. `OpenSearchClient.query()` runs search; hybrid passes `search_pipeline=hybrid-rrf`
6. Hits are normalized into `RetrieveHit` → `RetrieveResult`

For `run_experiment()`, the retriever preprocesses once, sets a shared `embedding` on the experiment request when k-NN/hybrid modes run, then delegates to the same `_execute_*` helpers used by `search_*`.

## Tests

| Path | Scope |
|------|--------|
| `tests/rag/retrieve.py` | `Retriever` helpers, search modes, experiment runner |
| `tests/rag/conftest.py` | Mocked BGE + OpenSearch fixtures |

Run: `uv sync --extra dev && uv run pytest tests/rag` (no live cluster required).

## Schema organization rationale

RAG domain models live under `src/services/rag/` so OpenSearch infrastructure stays reusable and separate from product logic. If the project grows, see [Roadmap](./roadmap-and-refactors.md) for schema consolidation options.

## Changelog

| Date | Change |
|------|--------|
| 2026-06-17 | Documented tests/, embedding-on-request flow, `RetrievalMode` experiment results |
| 2026-06-11 | Documented DDXPlus mapping and migration |
| 2026-06-09 | Initial structure guide |
