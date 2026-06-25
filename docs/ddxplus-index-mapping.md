# DDXPlus index mapping guide

> **Version:** 2026-06-25
> **Audience:** Data / ingest team
> **Dataset:** DDXPlus Design A (49-condition knowledge base)

This guide describes the OpenSearch index schema for the DDXPlus knowledge base, how to prepare documents for bulk ingest, and how to apply the index migration.

## Overview

| Item | Value |
|------|-------|
| Mapping file | [`indices/diseases/ddxplus_mapping.json`](../indices/diseases/ddxplus_mapping.json) |
| Physical index | `ddxplus_diseases` |
| Query alias | `diseases` (see `RETRIEVE_INDEX_ALIAS` in `.env`) |
| Migration script | [`src/migrations/migrate_ddxplus_index.py`](../src/migrations/migrate_ddxplus_index.py) |
| Upgrade version UUID | `6faf44c9-5214-4488-8e28-84b9362a1389` |
| Downgrade version UUID | `89f864ff-138b-4847-b9ef-2906d1971fa8` (restores Symptom2Disease `init_mapping.json`) |
| Corpus size | 49 documents (one per pathology in `release_conditions.json`) |

The Symptom2Disease mapping ([`init_mapping.json`](../indices/diseases/init_mapping.json)) remains in the repo for the original bootstrap path. Do not edit it in place when working on DDXPlus — use `ddxplus_mapping.json` and the migration script instead.

**Background:** Design A (DDXPlus-centric) rationale, dataset schema, and evaluation guidance are in the [Phase 1 review PDF](./AIO_MedPharmBioNexus_Phase1_Review-ThNg-June.10.2026_corrected.pdf) (Q1.2, Q3.1, Q5).

## Apply the new index

Prerequisites: `.env` configured with OpenSearch credentials; cluster reachable.

```bash
# First-time bootstrap (search pipeline + Symptom2Disease index) — only if cluster is empty
uv run python -m src.migrations.init_db upgrade

# Apply DDXPlus mapping (creates ddxplus_diseases, moves alias, deletes init_diseases)
uv run python -m src.migrations.migrate_ddxplus_index upgrade
```

Rollback to the Symptom2Disease mapping:

```bash
uv run python -m src.migrations.migrate_ddxplus_index downgrade
```

**Important:** Migration changes index schema and alias only. It does **not** copy or re-embed documents. Run your ingest pipeline after `upgrade`.

## Mapping comparison

| Field | `init_mapping.json` (Symptom2Disease) | `ddxplus_mapping.json` (DDXPlus) |
|-------|------------------------------|-----------------------------------|
| `doc_id` | keyword | keyword — set to DDXPlus `icd10-id` |
| `disease` | text + `raw` keyword | text + `raw` keyword — `cond-name-eng` |
| `symptoms` | keyword[] | keyword[] — resolved evidence names |
| `antecedents` | — | **keyword[]** — resolved antecedent names |
| `severity` | keyword | **integer** `1`–`5` (`1` = most severe) |
| `description` | text | text — **synthesized at ETL** (not in DDXPlus raw) |
| `precautions` | keyword | **removed** |
| `source` | — | **keyword** — e.g. `"ddxplus"` |
| `keyword_text` | text (BM25) | text (BM25) |
| `embedding` | knn_vector 384, cosine | knn_vector 384, cosine |

## Field reference

### Search fields

| Field | OpenSearch type | Used by | Notes |
|-------|-----------------|---------|-------|
| `keyword_text` | `text` | **BM25** (`match` query) | Concatenate disease + symptoms + antecedents. Analyzed/tokenized. |
| `embedding` | `knn_vector` (384) | **k-NN** | BGE-small-en-v1.5, L2-normalized, **no query prefix** at doc ingest. |

BM25 does **not** run on `keyword`-typed fields (`symptoms`, `antecedents`, `doc_id`). Always populate `keyword_text` for lexical retrieval.

### Metadata fields (returned in `_source`, not primary search)

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `doc_id` | keyword | `icd10-id` | Stable document id; also used as OpenSearch `_id`. |
| `disease` | text | `cond-name-eng` | Must **exactly match** patient CSV `PATHOLOGY` for eval. |
| `disease.raw` | keyword (subfield) | same as `disease` | Exact-match filtering / grouping. |
| `symptoms` | keyword[] | `symptoms` + `release_evidences.json` | Structured list for display / reranker / LLM. |
| `antecedents` | keyword[] | `antecedents` + `release_evidences.json` | Same resolution as symptoms. |
| `severity` | integer | `severity` | Native DDXPlus scale: `1` = most severe, `5` = least severe. |
| `description` | text | ETL-generated | LLM context; keep out of embedding if possible. |
| `source` | keyword | constant | `"ddxplus"` |

Do **not** index a separate `icd10_id` field — `doc_id` is the ICD-10 code.

Do **not** send `precautions` — the field is not in the DDXPlus mapping.

## Three logical views (ingest ETL)

Each disease record is projected into three views before indexing (see Technical Proposal §3.1):

| View | Stored in index? | Purpose |
|------|------------------|---------|
| **Embedded text** | No (used only to compute `embedding`) | Symptom-first natural language for dense retrieval |
| **Keyword text** | Yes → `keyword_text` | BM25 lexical search |
| **Metadata** | Yes → `_source` fields | Display, reranking, LLM generation |

### Embedded text template

Same as ``src.services.rag.preprocess.build_embed_text`` and ``scripts/build_kb.py``:

```python
def build_embed_text(disease: str, symptoms: list[str], antecedents: list[str]) -> str:
    symptom_str = ", ".join(symptoms)
    antecedent_str = ", ".join(antecedents)
    return f"Disease: {disease}. Symptoms: {symptom_str}. Antecedents: {antecedent_str}."
```

Embed with `BAAI/bge-small-en-v1.5` **without** the BGE query prefix. L2-normalize before indexing.

Do **not** include `description` in the embedding source — it is synthesized ETL text for LLM context and skews vectors away from symptom-only patient queries.

### Keyword text template

```python
def build_keyword_text(
    disease: str, symptoms: list[str], antecedents: list[str]
) -> str:
    parts = [disease, *symptoms, *antecedents]
    return " ".join(parts)
```

### Description (synthetic)

DDXPlus `release_conditions.json` has no free-text description. Build one at ETL, for example:

```text
Condition characterized by: {symptoms}. Risk factors: {antecedents}.
```

## Example document

```json
{
  "doc_id": "G70.0",
  "disease": "Myasthenia gravis",
  "symptoms": ["fatigue", "muscle weakness", "drooping eyelid"],
  "antecedents": ["autoimmune disease"],
  "severity": 1,
  "description": "Condition characterized by: fatigue, muscle weakness, drooping eyelid. Risk factors: autoimmune disease.",
  "source": "ddxplus",
  "keyword_text": "Myasthenia gravis fatigue muscle weakness drooping eyelid autoimmune disease",
  "embedding": ["... 384 floats ..."]
}
```

Bulk upsert with deterministic id: `_id = doc_id`.

## Data sources (DDXPlus English)

| File | Use |
|------|-----|
| `release_conditions.json` | 49 pathologies — disease name, ICD-10, severity, symptom/antecedent dicts |
| `release_evidences.json` | Resolve evidence keys to English labels |
| Patient CSV | **Queries only** — not indexed; `PATHOLOGY` is ground truth |

Patient/eval files are **not committed** (licensed). Download from Figshare and place under `data/eval/`:

- `release_validate_patients` (CSV, unzip from `release_validate_patients.zip`)
- `release_evidences.json`

The pre-built KB is committed at `data/kb/kb_ddxplus.json` (49 docs). Raw `release_conditions.json` is only needed to regenerate the KB via `scripts/build_kb.py`.

Official sources: [mila-iqia/ddxplus](https://github.com/mila-iqia/ddxplus), [figshare English dataset](https://figshare.com/articles/dataset/DDXPlus_Dataset_English_/22687585).

## Ingest workflow

```text
release_conditions.json + release_evidences.json
  → scripts/build_kb.py (or load data/kb/kb_ddxplus.json)
  → DiseaseDocument records
  → Ingestion / RAGService.ingest()
      normalize_symptoms → embed embed_text → bulk upsert (chunked by INGEST_BATCH_SIZE)
  → diseases alias (49 docs)
```

Use [`DiseaseDocument` / `BulkIngestRequest`](../src/services/rag/schemas.py) with [`Ingestion`](../src/services/rag/ingest.py) or [`RAGService.ingest()`](../src/services/rag/pipeline.py). Text builders live in [`preprocess.py`](../src/services/rag/preprocess.py) (`build_embed_text`, `build_keyword_text`, `normalize_symptoms`).

Remote OpenSearch bulk writes may exceed the library default HTTP timeout — set `OPENSEARCH_TIMEOUT=60` (or higher) in `.env`.

Parallel live eval (`notebooks/exp02_live_eval.ipynb`) uses concurrent HTTP searches — set `OPENSEARCH_POOL_MAXSIZE` ≥ `EXP02_WORKERS` (default 16 / 8) to avoid urllib3 `Connection pool is full` warnings. Restart the notebook kernel after changing pool settings.

## Post-ingest validation

| Check | Expected |
|-------|----------|
| Document count | `49` |
| `doc_id` uniqueness | 49 unique ICD-10 codes |
| `severity` range | integers `1`–`5` only |
| `embedding` dimension | `384` per document |
| `PATHOLOGY` join | every `cond-name-eng` matches a `disease` in the index |
| BM25 smoke test | `match` on `keyword_text` returns relevant hits |
| kNN smoke test | vector query returns hits with `space_type: cosinesimil` |

```bash
# Count (via OpenSearch API or Dev Tools)
GET /diseases/_count
```

## Common mistakes

| Mistake | Fix |
|---------|-----|
| BM25 on `symptoms` field | Use `keyword_text` (`text` type) |
| Storing raw evidence keys in `symptoms` | Resolve via `release_evidences.json` |
| BGE query prefix on documents | Prefix only at **query** time, not doc embed |
| `severity` as string `"1"` | Send integer `1` |
| Sending `precautions: []` | Omit field — not in mapping |
| Duplicate `icd10_id` field | Use `doc_id` only |

## Related documents

| Document | Location |
|----------|----------|
| Phase 1 review — dataset & eval design | [`AIO_MedPharmBioNexus_Phase1_Review-ThNg-June.10.2026_corrected.pdf`](./AIO_MedPharmBioNexus_Phase1_Review-ThNg-June.10.2026_corrected.pdf) |
| Technical proposal (architecture, three logical views) | [`Technical Proposal.pdf`](./Technical%20Proposal.pdf) |
| Project README | [`README.md`](../README.md) |

## Changelog

| Date | Change |
|------|--------|
| 2026-06-25 | Document `OPENSEARCH_POOL_MAXSIZE` for parallel live eval |
| 2026-06-25 | Updated ingest workflow (`Ingestion`, `RAGService`, `preprocess.py`); eval data paths; `OPENSEARCH_TIMEOUT` |
| 2026-06-11 | Linked Phase 1 review PDF |
| 2026-06-11 | Initial DDXPlus mapping guide (Design A) |
