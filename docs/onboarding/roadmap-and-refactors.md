# Roadmap and refactors

> **Version:** 2026-06-26
> **See also:** [Getting started](./getting-started.md), [Project structure](./project-structure.md)

MVP status, planned features, and structural changes we may make as the project matures.

This document is the **authoritative source** for project status. Other docs link here rather than duplicating status tables.

## Target architecture

```
[Ingest — offline]
  dataset → normalize → build keyword_text / embed_text → BGE doc embed → bulk upsert

[Query — online]
  user symptoms → preprocess → BGE query embed → hybrid search (top 20)
                → rerank (top 5) → Qwen3 8B generate → API response
```

## MVP phases (Module 1)

### Phase 1 — Foundation (in progress)

| Item | Status | Notes |
|------|--------|-------|
| OpenSearch on Aiven (BM25 + k-NN) | Done | `diseases` alias → `ddxplus_diseases` |
| DDXPlus index mapping + migration | Done | `ddxplus_mapping.json`, `migrate_ddxplus_index.py` |
| Search pipeline `hybrid-rrf` (RRF) | Done | `src/migrations/init_db.py` |
| OpenSearch client (sync) | Done | `src/db/vector_db/opensearch.py` |
| OpenSearch wire/response schemas | Done | `src/schemas/` |
| BGE query embedding | Done | `TextEmbeddingService` |
| Retrieval (BM25 / k-NN / hybrid) | Done | `Retriever` + `run_experiment()` |
| Retrieval unit tests | Done | `tests/rag/` (mocked OpenSearch, BGE, reranker) |
| Example notebook | Done | `notebooks/walkthrough.ipynb` |
| EXP-02 live eval notebook | Done | `notebooks/exp02_live_eval.ipynb` — BM25 + dense + hybrid vs offline baselines; saves `live_eval_latest.json` |
| Slim retrieval responses | Done | `RetrieveResult` vs `ExperimentModeResult` |
| Query preprocessing (retrieval) | Done | `preprocess.py` — KB text builders + `PreprocessPipeline` (injected into `Retriever`) |
| bge-reranker-base reranking | Done | `RerankerService`, `Retriever.rerank()` |
| Retrieve → rerank pipeline wiring | Done | `RAGService.query()` — hybrid top 20 → rerank top 5 |
| Batch ingestion | Done | `Ingestion` — normalize, embed, chunked bulk upsert |
| Qwen3 8B generation | **Todo** | Prompt + local inference |
| FastAPI HTTP layer | **Todo** | Symptom query endpoint |
| Full pipeline wiring | **Todo** | ingest → generate in `pipeline.py` |

### Phase 2 — Production scaling (future)

| Area | Direction |
|------|-----------|
| OpenSearch | Paid Aiven plan, replicas, HNSW tuning |
| Embeddings | BioBERT / PubMedBERT evaluation |
| Reranker | Larger cross-encoder models |
| LLM | GPT-class or larger open models |
| Ops | Monitoring, eval metrics, feedback loops |


## Completed refactors (2026-06-09)

| Item | Status |
| --- | --- |
| Lazy model download on first `TextEmbeddingService` use | Done |
| OpenSearch `bulk()` API (generic, no domain logic) | Done |
| Split `services/rag/` into modules | Done |
| Ingestion implementation | Done | `Ingestion` — normalize, embed, chunked bulk upsert |

## Likely refactors (evaluate when needed)

### 1. Expand `services/inference/`

```
services/inference/
  embeddings/service.py  # text embeddings (done)
  reranker/service.py      # cross-encoder (done)
  llm/service.py           # Qwen3 generation (planned)
```

Shared concern: model path resolution, lazy loading, device selection.

### 2. API layer

```
src/api/
  main.py           # FastAPI app
  routes/query.py   # POST /query
  dependencies.py   # inject RAGService, OpenSearch client
```

Use `asyncio.to_thread` (or `asyncer.asyncify`) on service methods in routes — e.g.
`await asyncio.to_thread(retriever.retrieve, query)` — so the sync `OpenSearchClient`
stays the single data-access path for migrations and API alike.

### 3. Consolidate or split schemas

**Option A (current):** OpenSearch infra in `src/schemas/`, RAG DTOs in `services/rag/schemas.py`.
**Option B (if RAG grows):** Rename to `src/schemas/opensearch/` and `src/services/rag/contracts/`.

Stay with Option A until file count or import cycles force a split.

### 4. Experiment notebook

`notebooks/walkthrough.ipynb` walks through ingest, preprocessing, BM25 / k-NN / hybrid search, `run_experiment()`, composable rerank (`Retriever.rerank()`), and the production `RAGService.query()` path.

`notebooks/exp02_live_eval.ipynb` ingests `data/kb/kb_ddxplus.json` into live OpenSearch and compares BM25, dense kNN, and hybrid Hit@1 against committed EXP-02 baselines (requires DDXPlus eval data under `data/eval/`). Uses batched `embed_queries`, `asyncio.to_thread` for concurrent searches, `OPENSEARCH_POOL_MAXSIZE` for urllib3 pooling, and writes metrics to `experiments/exp02/results/live_eval_latest.json` — see [EXP-02 README](../experiments/exp02/README.md#live-notebook-tunables).

Experiment results are keyed by `RetrievalMode` (e.g. `comparison.results[RetrievalMode.HYBRID]`).

## What we are not planning (MVP scope)

- Multiple vector databases (OpenSearch is the single store)
- LangChain / LlamaIndex as required dependencies (optional wrappers only)
- Clinical diagnosis claims or HIPAA-grade compliance
- Microservices split (monolith Python app is fine for Module 1)

## Changelog

| Date | Change |
|------|--------|
| 2026-06-26 | EXP-02 live eval save/load; full validate live results in `live_eval_latest.json` |
| 2026-06-25 | Documented EXP-02 live eval perf tuning (`EXP02_WORKERS`, `OPENSEARCH_POOL_MAXSIZE`) |
| 2026-06-25 | Documented EXP-02 live eval notebook; preprocess module split (KB builders + query pipeline) |
| 2026-06-20 | Renamed `ai_inference/` → `inference/`; `TextEmbeddingService`, `RerankerService` |
| 2026-06-20 | Marked reranker and retrieve → rerank pipeline done |
| 2026-06-17 | Marked retrieval tests and example notebook done; removed stale "no tests" row |
| 2026-06-11 | Merged duplicate architecture diagrams into one section |
| 2026-06-11 | DDXPlus mapping and migration marked done; ingest guide linked |
| 2026-06-09 | Initial roadmap reflecting services/ layout and RetrieveResult split |
