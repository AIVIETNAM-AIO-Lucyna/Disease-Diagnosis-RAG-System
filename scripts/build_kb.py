from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.services.rag.preprocess import (  # noqa: E402
    build_description,
    build_embed_text,
    build_keyword_text,
    choose_canonical_doc_id,
    normalize_icd10,
    normalize_symptom_phrase,
    split_icd10_codes,
)

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
    log.append("# KB build log \u2014 DDXPlus Design A (49 docs)\n")
    log.append(
        f"- conditions source: `{SRC_CONDITIONS.name}` ({len(conditions)} conditions)"
    )
    log.append(
        f"- evidences source: `{SRC_EVIDENCES.name}` ({len(evidences)} evidences)\n"
    )

    conds = list(conditions.values())
    raw_icds = [c.get("icd10-id", "") for c in conds]
    norm_icds = [normalize_icd10(x) for x in raw_icds]
    case_fixed = [(r, n) for r, n in zip(raw_icds, norm_icds) if r != n]
    canonical_doc_ids = [
        choose_canonical_doc_id(split_icd10_codes(c.get("icd10-id"))) for c in conds
    ]
    empty_doc_ids = [i for i, doc_id in enumerate(canonical_doc_ids) if not doc_id]
    duplicate_doc_ids = [
        k for k, v in Counter(canonical_doc_ids).items() if k and v > 1
    ]
    log.append("## ICD-10 normalization")
    log.append(f"- codes normalized (case/whitespace changed): {len(case_fixed)}")
    if case_fixed:
        log.append("  - " + ", ".join(f"`{r}`->`{n}`" for r, n in case_fixed))
    log.append(
        f"- canonical doc_id empty: {empty_doc_ids if empty_doc_ids else 'none'}"
    )
    log.append(
        f"- duplicate canonical doc_id: {duplicate_doc_ids if duplicate_doc_ids else 'none'}\n"
    )

    docs_norm: list[dict] = []
    docs_raw: list[dict] = []

    for cond in conds:
        disease = cond["cond-name-eng"]
        icd10_codes = split_icd10_codes(cond.get("icd10-id"))
        doc_id = choose_canonical_doc_id(icd10_codes)
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
        doc["_embed_text"] = build_embed_text(disease, symptoms, antecedents)
        docs_norm.append(doc)

        r_sym = dedup_keep_order([phrase(c, False) for c in sym_codes])
        r_ant = dedup_keep_order([phrase(c, False) for c in ant_codes])
        r_desc = build_description(r_sym, r_ant)
        docs_raw.append(
            {
                "doc_id": doc_id,
                "disease": disease,
                "symptoms": r_sym,
                "antecedents": r_ant,
                "severity": severity,
                "description": r_desc,
                "source": "ddxplus",
                "keyword_text": build_keyword_text(disease, r_sym, r_ant),
                "embedding": [],
            }
        )

    if embed:
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            for store in (docs_norm, docs_raw):
                texts = [
                    d.get("_embed_text")
                    or build_embed_text(d["disease"], d["symptoms"], d["antecedents"])
                    for d in store
                ]
                vecs = model.encode(texts, normalize_embeddings=True)
                for d, v in zip(store, vecs):
                    d["embedding"] = [float(x) for x in v]
            log.append(
                "## Embeddings\n- model: BAAI/bge-small-en-v1.5 (384-d, L2-normalized, no query prefix)\n"
            )
        except Exception as exc:
            log.append(
                f"## Embeddings\n- SKIPPED ({exc}); compute in ingest pipeline.\n"
            )

    for d in docs_norm:
        d.pop("_embed_text", None)

    (OUT_DIR / "kb_ddxplus.json").write_text(
        json.dumps(docs_norm, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "kb_ddxplus_rawq.json").write_text(
        json.dumps(docs_raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "kb_sample_one_disease.json").write_text(
        json.dumps(docs_norm[0], ensure_ascii=False, indent=2), encoding="utf-8"
    )

    n = len(docs_norm)
    uniq_ids = len({d["doc_id"] for d in docs_norm})
    sev_ok = all(
        isinstance(d["severity"], int) and 1 <= d["severity"] <= 5 for d in docs_norm
    )
    emb_dims = {len(d["embedding"]) for d in docs_norm}
    log.append("## Validation")
    log.append(f"- document count: {n} (expected 49) -> {'OK' if n == 49 else 'FAIL'}")
    log.append(
        f"- doc_id uniqueness: {uniq_ids}/{n} -> {'OK' if uniq_ids == n else 'FAIL'}"
    )
    log.append(f"- severity int in 1..5: {'OK' if sev_ok else 'FAIL'}")
    log.append(f"- embedding dims present: {emb_dims}")
    log.append("- precautions field: omitted")
    log.append(
        "- doc_id: canonical ICD-10 (multi-code sources resolved at build time)\n"
    )

    (OUT_DIR / "kb_build_log.md").write_text("\n".join(log), encoding="utf-8")

    print(
        f"Wrote {n} docs. unique ids={uniq_ids}. severity_ok={sev_ok}. emb_dims={emb_dims}"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--embed", action="store_true")
    args = ap.parse_args()
    build(embed=args.embed)
