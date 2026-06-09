# Roadmap and refactors

> **Version:** 2026-06-09  
> **See also:** [Getting started](./getting-started.md), [Project structure](./project-structure.md)

MVP status, planned features, and structural changes we may make as the project matures.

## MVP phases (Module 1)

### Phase 1 — Foundation (in progress)

| Item | Status | Notes |
|------|--------|-------|
| OpenSearch on Aiven (BM25 + k-NN) | Done | `init_diseases` index, `diseases` alias |
| Search pipeline `hybrid-rrf` (RRF) | Done | `src/migrations/init_db.py` |
| OpenSearch client (sync + async) | Done | `src/db/vector_db/opensearch.py` |
| OpenSearch wire/response schemas | Done | `src/schemas/` |
| BGE query embedding | Done | `BGEInferenceService` |
| Retrieval (BM25 / k-NN / hybrid) | Done | `Retriever` + experiment runner |
| Slim retrieval responses | Done | `RetrieveResult` vs `ExperimentModeResult` |
| Query preprocessing (retrieval) | Done | `preprocess.py` — used by `Retriever` |
| Batch ingestion | **Todo** | Stub in `ingest.py`; contracts only |
| bge-reranker-base reranking | **Todo** | `services/ai_inference/reranker/` |
| Qwen3 8B generation | **Todo** | Prompt + local inference |
| FastAPI HTTP layer | **Todo** | Symptom query endpoint |
| Full pipeline wiring | **Todo** | ingest -> rerank -> generate in `pipeline.py` |
| Automated tests | **Todo** | `tests/` directory configured, no tests yet |

### Phase 2 — Production scaling (future)

| Area | Direction |
|------|-----------|
| OpenSearch | Paid Aiven plan, replicas, HNSW tuning |
| Embeddings | BioBERT / PubMedBERT evaluation |
| Reranker | Larger cross-encoder models |
| LLM | GPT-class or larger open models |
| Ops | Monitoring, eval metrics, feedback loops |


## Target end-to-end flow

```
[Ingest - offline]
  dataset → normalize → build keyword_text / embed_text → BGE doc embed → bulk upsert

[Query - online]
  user query → preprocess → BGE query embed → hybrid search (top 20)
            → rerank (top 5) → LLM generate → API response
```

## Completed refactors (2026-06-09)

| Item | Status |
| --- | --- |
| Lazy model download on first `BGEInferenceService` use | Done |
| OpenSearch `bulk()` API (generic, no domain logic) | Done |
| Split `services/rag/` into modules | Done |
| Ingestion implementation | Other dev — stub in `ingest.py` |

## Likely refactors (evaluate when needed)

### 1. Expand `services/ai_inference/`

```
services/ai_inference/
  bge/service.py        # embeddings (done)
  reranker/service.py   # cross-encoder (planned)
  llm/service.py        # Qwen3 generation (planned)
```

Shared concern: model path resolution, lazy loading, device selection.

### 2. API layer

```
src/api/
  main.py           # FastAPI app
  routes/query.py   # POST /query
  dependencies.py   # inject RAGService, async OpenSearch
```

Use `AsyncOpenSearchClient` in routes; keep sync client for migrations.

### 3. Consolidate or split schemas

**Option A (current):** OpenSearch infra in `src/schemas/`, RAG DTOs in `services/rag/schemas.py`.  
**Option B (if RAG grows):** Rename to `src/schemas/opensearch/` and `src/services/rag/contracts/`.

Stay with Option A until file count or import cycles force a split.

### 4. Experiment CLI / notebook

Optional thin CLI or Jupyter examples under `examples/` for `run_experiment()` — keeps service layer free of print/debug code.

## What we are not planning (MVP scope)

- Multiple vector databases (OpenSearch is the single store)
- LangChain / LlamaIndex as required dependencies (optional wrappers only)
- Clinical diagnosis claims or HIPAA-grade compliance
- Microservices split (monolith Python app is fine for Module 1)

## Changelog

| Date | Change |
|------|--------|
| 2026-06-09 | Initial roadmap reflecting services/ layout and RetrieveResult split |
