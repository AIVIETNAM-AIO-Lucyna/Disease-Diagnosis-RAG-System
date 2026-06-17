# Development philosophy

> **Version:** 2026-06-17
> **See also:** [Project structure](./project-structure.md), [Roadmap](./roadmap-and-refactors.md)

How we build this project — conventions, patterns, and decision rules for contributors.

## Core principles

### 1. MVP first, production-aware

Ship the Module 1 pipeline end-to-end before optimizing. At the same time:

- Assume real infrastructure (Aiven OpenSearch, env-based secrets)
- No experimental hacks in shared paths
- Idempotent migrations and ingest (`_id = doc_id`)

### 2. Educational scope

The system is **not** a clinical diagnostic tool. The LLM summarizes retrieved disease information. Prompts and API copy should express uncertainty when evidence is weak.

### 3. Explicit layer boundaries

| Layer | May depend on | Must not contain |
|-------|---------------|------------------|
| `db/vector_db/` | settings, OpenSearch schemas | Embedding logic, prompt construction |
| `schemas/` (OpenSearch) | base models only | RAG business rules |
| `services/rag/` | db, ai_inference, rag schemas | Raw OpenSearch client calls scattered in handlers |
| `services/ai_inference/` | settings | OpenSearch queries |

Keep **prompt construction**, **model invocation**, and **post-processing** in separate modules.

### 4. Schemas are contracts

We use two Pydantic base types for OpenSearch integration:

```python
class RWSBaseModel:
    def to_dict(self) -> dict: ...

class ORSBaseModel:
    @classmethod
    def from_opensearch(cls, raw): ...
```

RAG-facing DTOs in `services/rag/schemas.py` follow the same idea: requests expose `to_search_body()`; responses are slim and purpose-specific. Vector/hybrid requests store the query vector on `embedding`; the retriever sets it before building the search body.

**Rule:** If it crosses a network boundary (OpenSearch, LLM API), it gets an explicit schema.

### 5. Settings over hardcoding

Index alias, source fields, search pipeline name, model paths, and credentials live in `src/settings.py` and `.env`. Code defaults should match migration scripts.

### 6. Experiment-friendly retrieval

The team compares retrieval strategies before locking the pipeline:

- `search_bm25()` — lexical baseline
- `search_vector()` — semantic baseline
- `search_hybrid()` — BM25 + k-NN + RRF (MVP default)
- `run_experiment()` — side-by-side comparison; results keyed by `RetrievalMode`

Production callers use slim `RetrieveResult`. Debug metadata stays on experiment types only (`ExperimentModeResult`, optional `opensearch_body`).

### 7. OpenSearch does search; the app does AI

| Component | Runs where |
|-----------|------------|
| BM25, k-NN, RRF fusion | OpenSearch (Aiven) |
| BGE embeddings | Application |
| Cross-encoder reranker | Application |
| LLM generation | Application |

Vectors are computed in Python and sent in the k-NN sub-query.

### 8. Symptom-first indexing

User queries are symptom lists. Searchable text must be **symptom-dense**:

- **`keyword_text`** (text) — BM25 field: disease + symptoms + antecedents
- **`embedding`** — built from symptom-first natural language at ingest
- **`symptoms`**, **`antecedents`** (keyword[]) — structured for display/rerank, not BM25

Use `match` on `keyword_text`, not on `keyword`-typed fields.

### 9. Minimal, safe diffs

- Match existing naming and folder conventions
- Do not rename public functions without updating all call sites
- Avoid drive-by refactors in unrelated files
- Prefer small incremental PRs over large rewrites

### 10. Fail loudly

Every IO path (OpenSearch, model load, file read) should surface meaningful errors. Do not swallow exceptions silently.

## Code style

| Topic | Convention |
|-------|------------|
| Python | 3.10+, type hints on public APIs |
| Formatting | ruff + pre-commit (see README) |
| Docstrings | Module + public class/method; Args/Returns for non-obvious params |
| Tests | `tests/` with pytest; mock external IO (OpenSearch, models) in service tests |
| Commits | Focus on *why*; only commit when asked |

## Sync client, async routes

- **`OpenSearchClient` (sync)** — single client for migrations, CLI, notebooks, ingest, and retrieval
- **FastAPI routes** — wrap blocking service calls with `asyncio.to_thread` or `asyncer.asyncify` at the route/service boundary; do not add a parallel async OpenSearch client unless load requires native async I/O

## Configuration and secrets

- `.env` for local development only — **never commit**
- Reference variable names in docs, not values
- Model weights under `models/` — gitignored, downloaded via `snapshot_download`

## Review checklist

Before opening a PR, verify:

- [ ] Full path traced (request → service → OpenSearch → response)
- [ ] Schemas updated if API shape changed
- [ ] Settings used instead of new magic strings
- [ ] No secrets in code or docs
- [ ] Backward compatibility considered for public service methods
- [ ] Tests added or updated for non-trivial behavior (`uv run pytest`)
- [ ] Edge cases and failure modes handled or documented

## Changelog

| Date | Change |
|------|--------|
| 2026-06-17 | Embedding-on-request pattern; retrieval tests; ruff/pre-commit |
| 2026-06-11 | Streamlined document; removed duplicate project description |
| 2026-06-09 | Initial philosophy doc |
