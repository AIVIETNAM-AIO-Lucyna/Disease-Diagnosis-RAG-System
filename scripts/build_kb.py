from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
SRC_CONDITIONS = DATA_DIR / "release_conditions.json"
SRC_EVIDENCES = DATA_DIR / "release_evidences.json"

_CANDIDATES = [
    DATA_DIR,
    DATA_DIR.parent,
    DATA_DIR.parent.parent,
    Path("/sessions/loving-happy-noether/mnt/AIO-Project"),
]
for base in _CANDIDATES:
    if (base / "release_conditions.json").exists():
        SRC_CONDITIONS = base / "release_conditions.json"
        SRC_EVIDENCES = base / "release_evidences.json"
        break

OUT_DIR = DATA_DIR

_OVERRIDES: dict[str, str] = {
    "Do you feel pain somewhere?": "pain present",
    "Characterize your pain:": "pain character",
    "How intense is the pain?": "pain intensity",
    "Does the pain radiate to another location?": "pain radiation",
    "How precisely is the pain located?": "pain location",
    "How fast did the pain appear?": "pain onset speed",
    "Do you have pain somewhere, related to your reason for consulting?": "pain related to consultation",
    "What color is the rash?": "rash color",
    "Do your lesions peel off?": "lesions peel off",
    "Is the rash swollen?": "rash swollen",
    "Where is the affected region located?": "rash location",
    "How intense is the pain caused by the rash?": "rash pain intensity",
    "Is the lesion (or are the lesions) larger than 1cm?": "lesion larger than 1cm",
    "How severe is the itching?": "itching severity",
    "Where is the swelling located?": "swelling location",
    "Have you traveled out of the country in the last 4 weeks?": "recent international travel",
    "Do you have a fever (either felt or measured with a thermometer)?": "fever",
    "Do you have a cough?": "cough",
    "Do you have nasal congestion or a clear runny nose?": "nasal congestion / runny nose",
    "Do you have diffuse (widespread) muscle pain?": "diffuse muscle pain",
    "Do you have high blood pressure or do you take medications to treat high blood pressure?": "high blood pressure",
    "Have you ever had a heart attack or do you have angina (chest pain)?": "heart attack or angina",
    "Do you have asthma or have you ever had to use a bronchodilator in the past?": "asthma",
    "Do you feel like you are dying or were you afraid that you were about do die?": "fear of dying",
}

_LEAD_FRAMES = [
    r"^do you have a known\b", r"^do you have any\b", r"^do you have an\b",
    r"^do you have\b", r"^do you feel\b", r"^do you ever\b",
    r"^did you previously,? or do you currently,? have any\b", r"^did you\b",
    r"^have you ever been diagnosed with\b", r"^have you ever had\b",
    r"^have you ever felt like you were\b", r"^have you ever\b",
    r"^have you recently had\b", r"^have you recently\b",
    r"^have you noticed any\b", r"^have you started or taken any\b",
    r"^are you experiencing\b", r"^are you feeling\b",
    r"^are you consulting because you have\b",
    r"^do you currently,? or did you ever,? have\b", r"^do you currently take\b",
    r"^do you take a\b", r"^do you take\b", r"^do you suffer from\b",
    r"^do you feel that\b", r"^do you feel like\b", r"^do you think you are\b",
    r"^have you had a\b", r"^have you had one or several\b", r"^have you had\b",
    r"^have you been\b", r"^have you noticed\b", r"^have any of your\b",
    r"^were you diagnosed with\b", r"^were you\b",
    r"^are you currently taking or have you recently taken\b",
    r"^are you currently\b", r"^are you\b", r"^is the\b", r"^is your\b",
    r"^how\b", r"^characterize your\b", r"^what\b", r"^where\b", r"^do you\b",
]


def normalize_symptom_phrase(question: str) -> str:
    q = question.strip()
    if q in _OVERRIDES:
        return _OVERRIDES[q]
    s = q.lower()
    s = re.sub(r"\s*\([^)]*\)", "", s)
    s = s.rstrip(" ?.!")
    for frame in _LEAD_FRAMES:
        new = re.sub(frame, "", s).strip()
        if new != s:
            s = new
            break
    s = re.split(
        r"\b(?:,?\s*(?:or|and)\s+(?:do|did|have|has|are|were|is)\s+(?:you|your))\b", s
    )[0]
    s = re.sub(r"^(been|had|a|an|the|any|with|that|to)\b\s*", "", s).strip()
    s = re.sub(r"\s+", " ", s).strip(" ,;:")
    return s or question.strip().lower()


def normalize_icd10(code: str) -> str:
    return (code or "").strip().upper()


def build_keyword_text(disease: str, symptoms: list[str], antecedents: list[str]) -> str:
    return " ".join([disease, *symptoms, *antecedents])


def build_embed_text(disease: str, symptoms: list[str], description: str) -> str:
    return f"Disease: {disease}. Symptoms: {', '.join(symptoms)}. {description}"


def build_description(symptoms: list[str], antecedents: list[str]) -> str:
    desc = f"Condition characterized by: {', '.join(symptoms)}."
    if antecedents:
        desc += f" Risk factors: {', '.join(antecedents)}."
    return desc


def dedup_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def build(embed: bool = False) -> None:
    conditions = json.loads(SRC_CONDITIONS.read_text(encoding="utf-8"))
    evidences = json.loads(SRC_EVIDENCES.read_text(encoding="utf-8"))

    def phrase(code: str, normalized: bool) -> str:
        q = evidences.get(code, {}).get("question_en", code)
        return normalize_symptom_phrase(q) if normalized else q

    log: list[str] = []
    log.append("# KB build log — DDXPlus Design A (49 docs)\n")
    log.append(f"- conditions source: `{SRC_CONDITIONS.name}` ({len(conditions)} conditions)")
    log.append(f"- evidences source: `{SRC_EVIDENCES.name}` ({len(evidences)} evidences)\n")

    raw_icds = [c.get("icd10-id", "") for c in conditions.values()]
    norm_icds = [normalize_icd10(x) for x in raw_icds]
    case_fixed = [(r, n) for r, n in zip(raw_icds, norm_icds) if r != n]
    dup_icds = [k for k, v in Counter(norm_icds).items() if v > 1]
    log.append("## ICD-10 normalization")
    log.append(f"- codes normalized (case/whitespace changed): {len(case_fixed)}")
    if case_fixed:
        log.append("  - " + ", ".join(f"`{r}`->`{n}`" for r, n in case_fixed))
    log.append(f"- duplicate ICD-10 after normalization: {dup_icds if dup_icds else 'none'}\n")

    docs_norm: list[dict] = []
    docs_raw: list[dict] = []

    for cond in conditions.values():
        disease = cond["cond-name-eng"]
        doc_id = normalize_icd10(cond.get("icd10-id"))
        severity = int(cond.get("severity"))

        sym_codes = cond.get("symptoms", [])
        ant_codes = cond.get("antecedents", [])

        symptoms = dedup_keep_order([phrase(c, True) for c in sym_codes])
        antecedents = dedup_keep_order([phrase(c, True) for c in ant_codes])
        description = build_description(symptoms, antecedents)

        doc = {
            "doc_id": doc_id,
            "disease": disease,
            "symptoms": symptoms,
            "antecedents": antecedents,
            "severity": severity,
            "description": description,
            "source": "ddxplus",
            "keyword_text": build_keyword_text(disease, symptoms, antecedents),
            "embedding": [],
        }
        doc["_embed_text"] = build_embed_text(disease, symptoms, description)
        docs_norm.append(doc)

        r_sym = dedup_keep_order([phrase(c, False) for c in sym_codes])
        r_ant = dedup_keep_order([phrase(c, False) for c in ant_codes])
        r_desc = build_description(r_sym, r_ant)
        docs_raw.append({
            "doc_id": doc_id,
            "disease": disease,
            "symptoms": r_sym,
            "antecedents": r_ant,
            "severity": severity,
            "description": r_desc,
            "source": "ddxplus",
            "keyword_text": build_keyword_text(disease, r_sym, r_ant),
            "embedding": [],
        })

    if embed:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            for store in (docs_norm, docs_raw):
                texts = [
                    d.get("_embed_text") or build_embed_text(d["disease"], d["symptoms"], d["description"])
                    for d in store
                ]
                vecs = model.encode(texts, normalize_embeddings=True)
                for d, v in zip(store, vecs):
                    d["embedding"] = [float(x) for x in v]
            log.append("## Embeddings\n- model: BAAI/bge-small-en-v1.5 (384-d, L2-normalized, no query prefix)\n")
        except Exception as exc:
            log.append(f"## Embeddings\n- SKIPPED ({exc}); compute in ingest pipeline.\n")

    for d in docs_norm:
        d.pop("_embed_text", None)

    (OUT_DIR / "kb_ddxplus.json").write_text(
        json.dumps(docs_norm, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "kb_ddxplus_rawq.json").write_text(
        json.dumps(docs_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "kb_sample_one_disease.json").write_text(
        json.dumps(docs_norm[0], ensure_ascii=False, indent=2), encoding="utf-8")

    n = len(docs_norm)
    uniq_ids = len({d["doc_id"] for d in docs_norm})
    sev_ok = all(isinstance(d["severity"], int) and 1 <= d["severity"] <= 5 for d in docs_norm)
    emb_dims = {len(d["embedding"]) for d in docs_norm}
    log.append("## Validation")
    log.append(f"- document count: {n} (expected 49) -> {'OK' if n == 49 else 'FAIL'}")
    log.append(f"- doc_id uniqueness: {uniq_ids}/{n} -> {'OK' if uniq_ids == n else 'FAIL'}")
    log.append(f"- severity int in 1..5: {'OK' if sev_ok else 'FAIL'}")
    log.append(f"- embedding dims present: {emb_dims}")
    log.append("- precautions field: omitted")
    log.append("- separate icd10_id field: omitted (doc_id = ICD-10)\n")

    log.append("## Symptom normalization spot-check (raw question -> phrase)")
    used_codes: list[str] = []
    for cond in conditions.values():
        used_codes.extend(cond.get("symptoms", []))
        used_codes.extend(cond.get("antecedents", []))
    seen: set[str] = set()
    for code in used_codes:
        q = evidences.get(code, {}).get("question_en", code)
        if q in seen:
            continue
        seen.add(q)
        log.append(f"- `{q}`  ->  **{normalize_symptom_phrase(q)}**")
        if len(seen) >= 24:
            break
    log.append("")

    log.append("## Patient/eval-set duplicate rows")
    log.append(
        "- 101 exact-duplicate rows (~0.075%) live in the patient/eval CSVs, not in this KB.\n"
        "- The KB is built from release_conditions.json (49 unique conditions), so no dup risk here.\n"
        "- Eval set is deduped separately (see dedup_eval.py), keeping first and logging dropped ids.\n"
    )

    (OUT_DIR / "kb_build_log.md").write_text("\n".join(log), encoding="utf-8")

    print(f"Wrote {n} docs. unique ids={uniq_ids}. severity_ok={sev_ok}. emb_dims={emb_dims}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--embed", action="store_true")
    args = ap.parse_args()
    build(embed=args.embed)
