#!/usr/bin/env python3
"""EXP-02 retrieval eval harness (offline, dependency-free BM25).

Ground truth: DDXPlus validate patients (PATHOLOGY = gold disease label).
Corpus: 49-doc DDXPlus KB (kb_ddxplus_FIXED.json).
Query text per patient: evidence codes -> normalize_symptom_phrase(question_en),
using the SAME normalizer as build_kb (so KB-time and query-time text are consistent).

Metrics: Hit@1, Hit@3, Hit@5, MRR.
A/B-1 (BM25 field): keyword_text  vs  keyword_text + description.

Dense / hybrid (RRF) are NOT run here: the FIXED KB has empty embeddings and the
sandbox has no BGE model / OpenSearch cluster. Code path is provided but guarded.
"""
import ast, csv, json, math, re, importlib.util, collections, sys, random, os, zipfile
from pathlib import Path

# Set EXP02_DATA to the folder holding the data files (defaults to /data).
DATA = Path(os.environ.get("EXP02_DATA", "/data"))
KB_PATH = DATA / "kb_ddxplus_FIXED.json"
CONDS = DATA / "release_conditions.json"
EVID = DATA / "release_evidences.json"
PATIENTS = DATA / "eval" / "release_validate_patients"
# normalizer: look in bundle root first, then the repo layout
_norm_candidates = [DATA / "ddxplus_normalize.py", DATA / "fix" / "src" / "services" / "rag" / "ddxplus_normalize.py"]
NORM_PATH = next((p for p in _norm_candidates if p.exists()), _norm_candidates[-1])
# auto-unzip the validate patients file if only the .zip is present
if not PATIENTS.exists():
    for _z in (DATA / "release_validate_patients.zip", DATA / "eval" / "release_validate_patients.zip"):
        if _z.exists():
            PATIENTS.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(_z) as _zf:
                _zf.extractall(PATIENTS.parent)
            break

SAMPLE = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0 = full set
SEED = 13

# ---- load the repo normalizer directly (avoid package __init__ -> opensearch import) ----
spec = importlib.util.spec_from_file_location("ddxplus_normalize", NORM_PATH)
nz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nz)
normalize_symptom_phrase = nz.normalize_symptom_phrase

# ---- tokenizer (shared by docs and queries) ----
TOK = re.compile(r"[a-z0-9]+")
def tokenize(text: str):
    return TOK.findall(text.lower())

# ---- load KB ----
kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
assert isinstance(kb, list), "expected list of docs"
diseases = [d["disease"] for d in kb]
disease_to_idx = {d: i for i, d in enumerate(diseases)}
assert len(disease_to_idx) == len(kb), "disease names not unique"
N = len(kb)

# ---- evidence code -> normalized phrase (precompute once) ----
evidences = json.loads(EVID.read_text(encoding="utf-8"))
code_phrase = {}
for code, meta in evidences.items():
    code_phrase[code] = normalize_symptom_phrase(meta.get("question_en", code))

def base_code(ev: str) -> str:
    # 'E_55_@_V_167' -> 'E_55' ; 'E_56_@_2' -> 'E_56' ; 'E_7' -> 'E_7'
    return ev.split("_@_")[0]

def patient_query_text(evidences_field: str) -> str:
    try:
        items = ast.literal_eval(evidences_field)
    except Exception:
        items = []
    phrases, seen = [], set()
    for ev in items:
        bc = base_code(str(ev))
        ph = code_phrase.get(bc)
        if ph and ph not in seen:
            seen.add(ph)
            phrases.append(ph)
    return " ".join(phrases)

# ---- BM25 index builder for a given doc-text function ----
class BM25:
    def __init__(self, doc_texts, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs_tokens = [tokenize(t) for t in doc_texts]
        self.doc_len = [len(t) for t in self.docs_tokens]
        self.avgdl = sum(self.doc_len) / len(self.doc_len)
        self.tf = []          # list of {term: freq}
        self.inverted = collections.defaultdict(list)  # term -> [(doc_idx, freq)]
        df = collections.Counter()
        for i, toks in enumerate(self.docs_tokens):
            c = collections.Counter(toks)
            self.tf.append(c)
            for term, f in c.items():
                self.inverted[term].append((i, f))
                df[term] += 1
        self.N = len(doc_texts)
        self.idf = {t: math.log((self.N - d + 0.5) / (d + 0.5) + 1.0) for t, d in df.items()}

    def scores(self, query_terms):
        sc = [0.0] * self.N
        for t in set(query_terms):
            if t not in self.inverted:
                continue
            idf = self.idf[t]
            for i, f in self.inverted[t]:
                denom = f + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                sc[i] += idf * (f * (self.k1 + 1)) / denom
        return sc

# ---- two field variants ----
variants = {
    "keyword_text": [d["keyword_text"] for d in kb],
    "keyword_text+description": [d["keyword_text"] + " " + d.get("description", "") for d in kb],
}
indexes = {name: BM25(texts) for name, texts in variants.items()}

# ---- iterate patients ----
def rank_of_gold(scores, gold_idx):
    gold = scores[gold_idx]
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], diseases[i]))
    return order.index(gold_idx) + 1, gold

agg = {name: dict(h1=0, h3=0, h5=0, rr=0.0, n=0) for name in variants}
per_dis = {name: collections.defaultdict(lambda: dict(h1=0, rr=0.0, n=0)) for name in variants}
empty_q = 0

rows = []
with open(PATIENTS, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

if SAMPLE and SAMPLE < len(rows):
    random.seed(SEED)
    rows = random.sample(rows, SAMPLE)

for row in rows:
    path = row["PATHOLOGY"]
    gold_idx = disease_to_idx.get(path)
    if gold_idx is None:
        continue
    q = patient_query_text(row["EVIDENCES"])
    qt = tokenize(q)
    if not qt:
        empty_q += 1
        continue
    for name, bm in indexes.items():
        sc = bm.scores(qt)
        rank, _ = rank_of_gold(sc, gold_idx)
        a = agg[name]; a["n"] += 1
        if rank == 1: a["h1"] += 1
        if rank <= 3: a["h3"] += 1
        if rank <= 5: a["h5"] += 1
        a["rr"] += 1.0 / rank
        pd = per_dis[name][path]; pd["n"] += 1
        if rank == 1: pd["h1"] += 1
        pd["rr"] += 1.0 / rank

# ---- report ----
AFFECTED = {"Anemia","Bronchiectasis","Cluster headache","GERD","Guillain-Barré syndrome",
            "Localized edema","Panic attack","Pulmonary embolism","Tuberculosis"}

def pct(x, n): return f"{100.0*x/n:.2f}%" if n else "n/a"

lines = []
lines.append("# EXP-02 — BM25 retrieval eval (DDXPlus validate)\n")
lines.append(f"- Corpus: {N} KB docs (kb_ddxplus_FIXED.json)")
lines.append(f"- Queries: {agg[list(variants)[0]]['n']} patients (skipped empty queries: {empty_q}; total rows read: {len(rows)})")
lines.append(f"- Query text = normalize_symptom_phrase(question_en) of patient EVIDENCES (same normalizer as build_kb)")
lines.append(f"- BM25 Okapi k1=1.5 b=0.75; tie-break deterministic\n")
lines.append("## Overall metrics\n")
lines.append("| BM25 field variant | Hit@1 | Hit@3 | Hit@5 | MRR | n |")
lines.append("|---|---|---|---|---|---|")
for name, a in agg.items():
    n = a["n"]
    lines.append(f"| {name} | {pct(a['h1'],n)} | {pct(a['h3'],n)} | {pct(a['h5'],n)} | {a['rr']/n:.4f} | {n} |")

lines.append("\n## Per-disease Hit@1 / MRR (variant: keyword_text)\n")
lines.append("| Disease | Hit@1 | MRR | n | affected |")
lines.append("|---|---|---|---|---|")
base = per_dis["keyword_text"]
for dis in sorted(base, key=lambda d: base[d]["rr"]/base[d]["n"]):
    pd = base[dis]; n = pd["n"]
    flag = "⚠️" if dis in AFFECTED else ""
    lines.append(f"| {dis} | {pct(pd['h1'],n)} | {pd['rr']/n:.4f} | {n} | {flag} |")

report = "\n".join(lines)
(Path("/data/eval/EXP02_eval_report.md")).write_text(report, encoding="utf-8")

# per-disease csv (both variants)
with open("/data/eval/exp02_per_disease.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["variant","disease","n","hit1","hit1_pct","mrr","affected"])
    for name in variants:
        for dis, pd in per_dis[name].items():
            n = pd["n"]
            w.writerow([name, dis, n, pd["h1"], f"{100.0*pd['h1']/n:.2f}", f"{pd['rr']/n:.4f}", dis in AFFECTED])

print(report)
print("\n[written] /data/eval/EXP02_eval_report.md , /data/eval/exp02_per_disease.csv")
