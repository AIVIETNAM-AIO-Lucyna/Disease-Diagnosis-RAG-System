from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
for cand in (SRC, SRC.parent, Path("/sessions/loving-happy-noether/mnt/AIO-Project")):
    if (cand / "release_test_patients.zip").exists():
        SRC = cand
        break

SPLITS = {
    "train": SRC / "release_train_patients.zip",
    "validate": SRC / "release_validate_patients.zip",
    "test": SRC / "release_test_patients.zip",
}
EVAL_SPLITS = ["validate", "test"]
KEY = ["AGE", "SEX", "PATHOLOGY", "EVIDENCES"]


def identity_hash(df: pd.DataFrame) -> pd.Series:
    joined = df[KEY].astype(str).agg("␟".join, axis=1)
    return joined.map(lambda s: hashlib.md5(s.encode()).hexdigest())


def main() -> None:
    log: list[str] = ["# Eval-set dedup log — DDXPlus\n"]
    log.append(f"- source: `{SRC}`")
    log.append("- duplicate definition: exact match on ALL columns")
    log.append(
        "- policy: keep first occurrence, drop the rest, log dropped row indices\n"
    )

    id_hashes: dict[str, set[str]] = {}

    for split in ["train", "validate", "test"]:
        df = pd.read_csv(SPLITS[split])
        id_hashes[split] = set(identity_hash(df))

        if split not in EVAL_SPLITS:
            log.append(
                f"## {split}: {len(df):,} rows (not an eval split — identity cached for leakage check)\n"
            )
            continue

        dup_mask = df.duplicated(keep="first")
        n_dup = int(dup_mask.sum())
        dropped_idx = df.index[dup_mask].tolist()
        df_clean = df[~dup_mask].reset_index(drop=True)

        out_csv = HERE / f"release_{split}_patients_dedup.csv"
        df_clean.to_csv(out_csv, index=False)

        by_path = df.loc[dup_mask, "PATHOLOGY"].value_counts()

        log.append(f"## {split}")
        log.append(f"- original rows: {len(df):,}")
        log.append(f"- exact duplicates dropped: {n_dup}")
        log.append(f"- rows after dedup: {len(df_clean):,}")
        log.append(f"- output: `{out_csv.name}`")
        log.append(f"- duplicate share: {n_dup/len(df)*100:.4f}%")
        if n_dup:
            log.append("- dropped rows by PATHOLOGY:")
            for path, cnt in by_path.items():
                cls_size = int((df["PATHOLOGY"] == path).sum())
                log.append(
                    f"  - {path}: {cnt} dropped / {cls_size:,} in class ({cnt/cls_size*100:.3f}% of class)"
                )
            log.append(
                f"- dropped row indices (first 50 of {n_dup}): {dropped_idx[:50]}"
            )
        log.append("")

    log.append("## Cross-split overlap (leakage check)")
    log.append(
        "- key: (AGE, SEX, PATHOLOGY, EVIDENCES). Overlap here = same patient in two splits.\n"
    )
    for a, b in [("train", "validate"), ("train", "test"), ("validate", "test")]:
        ov = id_hashes[a] & id_hashes[b]
        log.append(f"- {a} ∩ {b}: {len(ov):,} overlapping identities")
    log.append("")

    (HERE / "dedup_eval_log.md").write_text("\n".join(log), encoding="utf-8")
    print("Done. See dedup_eval_log.md and *_dedup.csv")


if __name__ == "__main__":
    main()
