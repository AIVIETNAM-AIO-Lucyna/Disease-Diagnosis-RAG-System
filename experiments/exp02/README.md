# EXP-02 — Retrieval evaluation (DDXPlus validate)

Evaluate BM25, dense, and hybrid (RRF) retrieval of the 49-disease KB
against the DDXPlus validate split.

## Files
- `eval_retrieval.py`   — BM25 (Okapi k1=1.5, b=0.75). Writes the BM25 report + per-disease CSV.
- `eval_dense_hybrid.py`— Dense (BAAI/bge-small-en-v1.5) + Hybrid RRF(k=60). Prints a table to stdout.
- `results/`            — committed result artifacts (BM25 report, per-disease CSV, dense/hybrid summary).

## Data (NOT committed)
DDXPlus is licensed; patient data is not stored in the repo.
- Download `release_validate_patients.zip` from the DDXPlus dataset (Figshare).
- KB / conditions / evidences come from the repo (see the KB-regeneration PR).

## Reproduce (local)
    pip install -U sentence-transformers rank-bm25 numpy
    export EXP02_DATA=/path/to/exp02_inputs   # folder with KB + normalizer + patient data
    python eval_retrieval.py 132448           # BM25 (writes results/)
    python eval_dense_hybrid.py 132448        # dense + hybrid (prints table)

## Reproduce (Google Colab)
    # after mounting Drive and copying this folder to /content/exp02
    import os; os.makedirs("/data/eval", exist_ok=True)
    !EXP02_DATA=/content/exp02 python /content/exp02/eval_retrieval.py 132448
    !pip -q install -U sentence-transformers
    !EXP02_DATA=/content/exp02 python /content/exp02/eval_dense_hybrid.py 132448

## Config / provenance
- Embedding: BAAI/bge-small-en-v1.5 (384-dim, cosine)
- BM25: Okapi k1=1.5, b=0.75
- Hybrid: RRF k=60 (local fusion of BM25 + dense ranks)
- Query text excludes the disease name (avoid label leakage)
- SAMPLE arg = number of patients (default 5000; 132448 = full). Sampling random, SEED=13 (reproducible).
- Note: the BM25 report output path is currently hardcoded to /data/eval — create it
  first (`mkdir -p /data/eval`) or adjust the script before running locally.

## Headline results (full, n = 132,448)
- BM25 + description : Hit@1 98.78% (MRR 0.9937)
- Hybrid-RRF + desc  : Hit@1 91.95% (MRR 0.9570)
- Dense + desc       : Hit@1 84.28% (MRR 0.9027)
See `results/` for full tables and per-disease breakdown.