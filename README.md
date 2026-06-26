# Disease Diagnosis RAG System

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![OpenSearch](https://img.shields.io/badge/OpenSearch-k--NN%20%2B%20BM25-green.svg)](https://opensearch.org/)

**Educational RAG system** for disease symptom prediction — AIO Vietnam, Module 1.

> **Disclaimer:** Not a clinical diagnostic tool.

## Current status

Retrieval (BM25, k-NN, hybrid + RRF), cross-encoder reranking (`bge-reranker-base`), and batch ingestion are implemented with unit tests in `tests/rag/`. LLM generation and HTTP API are **Todo**.

See [Roadmap](./docs/onboarding/roadmap-and-refactors.md) for full MVP status.

## Quick start

```bash
uv sync
cp .env.example .env   # configure OPENSEARCH_* credentials
uv run python -m src.migrations.init_db upgrade
uv run python -m src.migrations.migrate_ddxplus_index upgrade
```

See [Getting started](./docs/onboarding/getting-started.md) for detailed setup and verification steps.

End-to-end demo: [`notebooks/walkthrough.ipynb`](./notebooks/walkthrough.ipynb) (ingest → retrieve → rerank).

Live eval vs EXP-02 baselines: [`notebooks/exp02_live_eval.ipynb`](./notebooks/exp02_live_eval.ipynb) (requires DDXPlus patient data under `data/eval/`). Latest full-run metrics are committed in [`experiments/exp02/results/live_eval_latest.json`](./experiments/exp02/results/live_eval_latest.json).

## Testing (before commit)

Install dev dependencies once (includes `pytest`):

```bash
uv sync --extra dev
```

Run the full test suite from the project root:

```bash
uv run pytest
```

Run only RAG service tests:

```bash
uv run pytest tests/rag
```

Tests use mocked OpenSearch and embedding services — no `.env` or live cluster required.

Before pushing, also run pre-commit hooks (lint, format, lockfile check):

```bash
uv run pre-commit run --all-files
```

Install hooks once so they run automatically on `git commit`:

```bash
uv run pre-commit install
```

## Documentation

Read these guides **once** when joining the project:

| # | Document | What you will learn |
|---|----------|---------------------|
| 1 | [Getting started](./docs/onboarding/getting-started.md) | Prerequisites, setup, first commands |
| 2 | [Project structure](./docs/onboarding/project-structure.md) | Folders, modules, layer responsibilities |
| 3 | [Development philosophy](./docs/onboarding/development-philosophy.md) | Conventions, patterns, code style |
| 4 | [Roadmap and refactors](./docs/onboarding/roadmap-and-refactors.md) | MVP status, planned work |

### Reference documents

| Document | Audience |
|----------|----------|
| [DDXPlus index mapping](./docs/ddxplus-index-mapping.md) | Data team — field schema, ingest workflow |
| [`Technical Proposal.pdf`](./docs/Technical Proposal.pdf) | All — original architecture design |
| [`indices/diseases/ddxplus_mapping.json`](./indices/diseases/ddxplus_mapping.json) | Data team — active OpenSearch mapping |

### Versioning policy

Documentation uses **date-based versions** (`YYYY-MM-DD`), not semver. Update the `Version` line at the top of a doc when its content meaningfully changes, and add a row to the **Changelog** section.

## Changelog

| Date | Change |
|------|--------|
| 2026-06-26 | EXP-02 live eval save/load (`live_eval_latest.json`); full validate results committed |
| 2026-06-25 | Document `OPENSEARCH_POOL_MAXSIZE`, urllib3 pool troubleshooting, EXP-02 eval tunables |
| 2026-06-25 | Document `OPENSEARCH_TIMEOUT`, EXP-02 live eval notebook; sync onboarding docs with ingest/preprocess API |
| 2026-06-25 | Document batch ingestion (`Ingestion`) and derived `keyword_text` |
| 2026-06-20 | Document reranker service and RAGService retrieve → rerank pipeline |
| 2026-06-17 | Note retrieval unit tests; onboarding docs synced with refactored Retriever |
| 2026-06-17 | Added testing and pre-commit guidance before commit |
| 2026-06-11 | Consolidated to single README; added DDXPlus mapping and migration |
| 2026-06-09 | Initial retrieval implementation |
