# EXP-02 — Dense + Hybrid retrieval eval (DDXPlus validate)

- Corpus: 49 KB docs (kb_ddxplus_FIXED.json)
- Queries: 132,448 patients (full validate set)
- Embedding: BAAI/bge-small-en-v1.5 (384-dim, cosine)
- Hybrid = Reciprocal Rank Fusion (RRF, k=60) over BM25 rank + dense rank, computed locally
- Query embed text excludes the disease name (gold label) to avoid leakage
- A/B-2: embed text with vs without `description`
- Same normalizer & ground truth (PATHOLOGY) as eval_retrieval.py (BM25)
- Run date: 2026-06-19 (reproduced on Google Colab)

## Dense + Hybrid (n = 132,448)

| config | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| dense (no-desc)      | 83.11% | 94.41% | 96.82% | 0.8911 |
| dense (with-desc)    | 84.28% | 95.48% | 98.46% | 0.9027 |
| hybrid-RRF (no-desc) | 91.17% | 98.89% | 99.61% | 0.9511 |
| hybrid-RRF (with-desc)| 91.95% | 99.52% | 99.77% | 0.9570 |

## Reference: BM25 (eval_retrieval.py, same data)

| BM25 variant | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| keyword_text              | 98.47% | 99.95% | 99.99%  | 0.9921 |
| keyword_text + description| 98.78% | 99.96% | 100.00% | 0.9937 |

## Notes
- On this lexically-aligned eval (query tokens overlap KB vocabulary), BM25 is strongest.
  This reflects the eval format, NOT an architectural conclusion about hybrid retrieval.
- `description` consistently helps all methods.
- Next steps: realistic / natural-language eval; tune RRF weighting (favor BM25, or
  cascade dense only on low-confidence); consider a medical-domain embedding.