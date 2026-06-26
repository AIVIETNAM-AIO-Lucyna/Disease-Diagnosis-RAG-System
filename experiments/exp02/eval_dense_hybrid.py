#!/usr/bin/env python3
"""EXP-02 dense + hybrid eval (RUN IN YOUR ENV: needs sentence-transformers + torch).

This is NOT runnable in the Notion sandbox (no BGE model / offline). Run locally:
    pip install sentence-transformers
    python3 eval_dense_hybrid.py [SAMPLE]

What it does
------------
- Dense retrieval over the 49-doc KB using BAAI/bge-small-en-v1.5 (384-dim), cosine.
- A/B-2 (embed text): WITHOUT description (current build_embed_text) vs WITH description.
- Hybrid = Reciprocal Rank Fusion (RRF, k=60) of BM25 ranks + dense ranks.
  (RRF computed locally; an OpenSearch cluster is NOT required to measure ranking quality.)
- Same ground truth + same query construction as eval_retrieval.py (shared normalizer).

NOTE on fairness: the query embedding text excludes the disease name (it is the gold label).
"""

import ast
import csv
import json
import math
import re
import importlib.util
import collections
import sys
import random
import os
import zipfile
from pathlib import Path

# Set EXP02_DATA to the folder holding the data files (defaults to /data).
DATA = Path(os.environ.get("EXP02_DATA", "/data"))
KB_PATH = DATA / "kb_ddxplus_FIXED.json"
EVID = DATA / "release_evidences.json"
PATIENTS = DATA / "eval" / "release_validate_patients"
_norm_candidates = [
    DATA / "ddxplus_normalize.py",
    DATA / "fix" / "src" / "services" / "rag" / "ddxplus_normalize.py",
]
NORM_PATH = next((p for p in _norm_candidates if p.exists()), _norm_candidates[-1])
if not PATIENTS.exists():
    for _z in (
        DATA / "release_validate_patients.zip",
        DATA / "eval" / "release_validate_patients.zip",
    ):
        if _z.exists():
            PATIENTS.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(_z) as _zf:
                _zf.extractall(PATIENTS.parent)
            break
MODEL = "BAAI/bge-small-en-v1.5"
SAMPLE = (
    int(sys.argv[1]) if len(sys.argv) > 1 else 5000
)  # default subsample (dense is heavier)
SEED = 13

spec = importlib.util.spec_from_file_location("ddxplus_normalize", NORM_PATH)
nz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nz)
normalize_symptom_phrase = nz.normalize_symptom_phrase

TOK = re.compile(r"[a-z0-9]+")
tokenize = lambda t: TOK.findall(t.lower())

kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
diseases = [d["disease"] for d in kb]
disease_to_idx = {d: i for i, d in enumerate(diseases)}
N = len(kb)

evidences = json.loads(EVID.read_text(encoding="utf-8"))
code_phrase = {
    c: normalize_symptom_phrase(m.get("question_en", c)) for c, m in evidences.items()
}
base_code = lambda ev: ev.split("_@_")[0]


def patient_phrases(evidences_field):
    try:
        items = ast.literal_eval(evidences_field)
    except Exception:
        items = []
    out, seen = [], set()
    for ev in items:
        ph = code_phrase.get(base_code(str(ev)))
        if ph and ph not in seen:
            seen.add(ph)
            out.append(ph)
    return out


# ---- BM25 (same as offline harness) ----
class BM25:
    def __init__(self, texts, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        toks = [tokenize(t) for t in texts]
        self.dl = [len(x) for x in toks]
        self.avgdl = sum(self.dl) / len(self.dl)
        self.inv = collections.defaultdict(list)
        df = collections.Counter()
        for i, tk in enumerate(toks):
            c = collections.Counter(tk)
            for term, f in c.items():
                self.inv[term].append((i, f))
                df[term] += 1
        self.N = len(texts)
        self.idf = {
            t: math.log((self.N - d + 0.5) / (d + 0.5) + 1) for t, d in df.items()
        }

    def scores(self, qt):
        sc = [0.0] * self.N
        for t in set(qt):
            if t in self.inv:
                for i, f in self.inv[t]:
                    sc[i] += (
                        self.idf[t]
                        * (f * (self.k1 + 1))
                        / (
                            f
                            + self.k1 * (1 - self.b + self.b * self.dl[i] / self.avgdl)
                        )
                    )
        return sc


bm25 = BM25([d["keyword_text"] + " " + d.get("description", "") for d in kb])

# ---- dense ----
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer(MODEL)


def embed_text_doc(d, with_desc):
    base = f"Disease: {d['disease']}. Symptoms: {', '.join(d['symptoms'])}. Antecedents: {', '.join(d['antecedents'])}."
    return base + (f" {d['description']}" if with_desc else "")


def embed_text_query(phrases):
    # disease name intentionally excluded (gold label)
    return f"Symptoms and antecedents: {', '.join(phrases)}."


def norm(m):
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)


doc_emb = {
    wd: norm(np.array(model.encode([embed_text_doc(d, wd) for d in kb])))
    for wd in (False, True)
}


def ranks_from_scores(scores):
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], diseases[i]))
    return {idx: r + 1 for r, idx in enumerate(order)}


def rrf(rank_lists, k=60):
    fused = collections.defaultdict(float)
    for rl in rank_lists:
        for idx, r in rl.items():
            fused[idx] += 1.0 / (k + r)
    return fused


rows = list(csv.DictReader(open(PATIENTS, encoding="utf-8")))
if SAMPLE and SAMPLE < len(rows):
    random.seed(SEED)
    rows = random.sample(rows, SAMPLE)

configs = [
    "dense(no-desc)",
    "dense(with-desc)",
    "hybrid-RRF(no-desc)",
    "hybrid-RRF(with-desc)",
]
agg = {c: dict(h1=0, h3=0, h5=0, rr=0.0, n=0) for c in configs}

for row in rows:
    gold = disease_to_idx.get(row["PATHOLOGY"])
    if gold is None:
        continue
    ph = patient_phrases(row["EVIDENCES"])
    if not ph:
        continue
    q = model.encode([embed_text_query(ph)])
    q = norm(np.array(q))
    bm_scores = bm25.scores(tokenize(" ".join(ph)))
    bm_ranks = ranks_from_scores(bm_scores)
    for wd, tag in ((False, "no-desc"), (True, "with-desc")):
        dsc = (doc_emb[wd] @ q[0]).tolist()
        dranks = ranks_from_scores(dsc)
        # dense
        c = f"dense({tag})"
        rank = dranks[gold]
        a = agg[c]
        a["n"] += 1
        a["h1"] += rank == 1
        a["h3"] += rank <= 3
        a["h5"] += rank <= 5
        a["rr"] += 1 / rank
        # hybrid
        fused = rrf([bm_ranks, dranks])
        order = sorted(fused, key=lambda i: (-fused[i], diseases[i]))
        hr = order.index(gold) + 1
        c = f"hybrid-RRF({tag})"
        a = agg[c]
        a["n"] += 1
        a["h1"] += hr == 1
        a["h3"] += hr <= 3
        a["h5"] += hr <= 5
        a["rr"] += 1 / hr

print(f"n={agg[configs[0]]['n']} (model={MODEL})")
print("| config | Hit@1 | Hit@3 | Hit@5 | MRR |")
print("|---|---|---|---|---|")
for c, a in agg.items():
    n = a["n"]
    f = lambda x: f"{100*x/n:.2f}%"
    print(f"| {c} | {f(a['h1'])} | {f(a['h3'])} | {f(a['h5'])} | {a['rr']/n:.4f} |")
