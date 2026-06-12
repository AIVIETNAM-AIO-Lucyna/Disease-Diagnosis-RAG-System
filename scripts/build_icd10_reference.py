#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the ICD-10 & severity reference table for the DDXPlus knowledge base.

The DDXPlus release ships an authoritative condition catalogue
(``release_conditions.json``) in which every pathology already carries an
official ICD-10 identifier and a clinical severity score (1 = most severe,
5 = least severe). This module turns that catalogue into a reviewable
reference artefact for the knowledge-base ingestion step:

    * the raw ICD-10 string is normalised (trimmed, upper-cased, split on commas);
    * each code is mapped to its official ICD-10 chapter by numeric range
      (not by leading letter, which is ambiguous for D/H);
    * a single canonical ``doc_id`` is chosen per condition;
    * a severity flag (``is_severe`` = severity <= SEVERE_THRESHOLD) is derived
      for the safety-oriented retrieval metric (MSR).

Outputs a CSV (machine-readable) and a Markdown audit (human review).

Project : Disease-Diagnosis-RAG-System — AIO 2026, Project 1
Team    : Med / Pharm / Bio Nexus
Author  : Nguyễn Văn Thương (Team Leader — Domain Expert)
Created : 2026-06-12
License : Internal use, AIO 2026 Conquer

Usage
-----
    python3 build_icd10_reference.py \
        --conditions release_conditions.json \
        --outdir . \
        --prefix icd10_audit
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

LOGGER = logging.getLogger("icd10_reference")

# Severity in DDXPlus is ordinal: 1 = most severe ... 5 = least severe.
# A condition is treated as "severe" (for the Most-Severe-Retrieval metric)
# when its score is at or below this threshold.
SEVERE_THRESHOLD = 2

# A handful of conditions in the source carry more than one ICD-10 code.
# Where the codes are not interchangeable we pin the canonical identifier
# explicitly so the choice is auditable rather than implicit.
#   J17 = "Pneumonia in diseases classified elsewhere" (a secondary/manifestation
#         code that should not stand alone), J18 = "Pneumonia, organism
#         unspecified" (the general stand-alone code) -> prefer J18.
CANONICAL_OVERRIDES: dict[tuple[str, ...], str] = {
    ("J17", "J18"): "J18",
}


@dataclass(frozen=True)
class Chapter:
    """An official ICD-10 chapter and its inclusive code range."""

    roman: str
    title: str
    code_range: str
    start: tuple[int, int]
    end: tuple[int, int]

    def contains(self, key: tuple[int, int]) -> bool:
        return self.start <= key <= self.end


def _bound(letter: str, number: int) -> tuple[int, int]:
    return (ord(letter), number)


# Official WHO ICD-10 chapters (I–XXII), ordered. Ranges that cross a letter
# boundary (e.g. Neoplasms C00–D49) are expressed with explicit bounds.
CHAPTERS: tuple[Chapter, ...] = (
    Chapter("I", "Certain infectious and parasitic diseases", "A00–B99", _bound("A", 0), _bound("B", 99)),
    Chapter("II", "Neoplasms", "C00–D49", _bound("C", 0), _bound("D", 49)),
    Chapter("III", "Diseases of the blood and immune mechanism", "D50–D89", _bound("D", 50), _bound("D", 89)),
    Chapter("IV", "Endocrine, nutritional and metabolic diseases", "E00–E89", _bound("E", 0), _bound("E", 89)),
    Chapter("V", "Mental, behavioural and neurodevelopmental disorders", "F01–F99", _bound("F", 1), _bound("F", 99)),
    Chapter("VI", "Diseases of the nervous system", "G00–G99", _bound("G", 0), _bound("G", 99)),
    Chapter("VII", "Diseases of the eye and adnexa", "H00–H59", _bound("H", 0), _bound("H", 59)),
    Chapter("VIII", "Diseases of the ear and mastoid process", "H60–H95", _bound("H", 60), _bound("H", 95)),
    Chapter("IX", "Diseases of the circulatory system", "I00–I99", _bound("I", 0), _bound("I", 99)),
    Chapter("X", "Diseases of the respiratory system", "J00–J99", _bound("J", 0), _bound("J", 99)),
    Chapter("XI", "Diseases of the digestive system", "K00–K95", _bound("K", 0), _bound("K", 95)),
    Chapter("XII", "Diseases of the skin and subcutaneous tissue", "L00–L99", _bound("L", 0), _bound("L", 99)),
    Chapter("XIII", "Diseases of the musculoskeletal system", "M00–M99", _bound("M", 0), _bound("M", 99)),
    Chapter("XIV", "Diseases of the genitourinary system", "N00–N99", _bound("N", 0), _bound("N", 99)),
    Chapter("XV", "Pregnancy, childbirth and the puerperium", "O00–O9A", _bound("O", 0), _bound("O", 99)),
    Chapter("XVI", "Certain conditions originating in the perinatal period", "P00–P96", _bound("P", 0), _bound("P", 96)),
    Chapter("XVII", "Congenital malformations and chromosomal abnormalities", "Q00–Q99", _bound("Q", 0), _bound("Q", 99)),
    Chapter("XVIII", "Symptoms, signs and abnormal clinical findings", "R00–R99", _bound("R", 0), _bound("R", 99)),
    Chapter("XIX", "Injury, poisoning and external causes", "S00–T88", _bound("S", 0), _bound("T", 88)),
    Chapter("XX", "External causes of morbidity", "V00–Y99", _bound("V", 0), _bound("Y", 99)),
    Chapter("XXI", "Factors influencing health status", "Z00–Z99", _bound("Z", 0), _bound("Z", 99)),
    Chapter("XXII", "Codes for special purposes", "U00–U85", _bound("U", 0), _bound("U", 85)),
)


@dataclass
class ConditionReference:
    """A single reviewable reference row."""

    disease: str
    icd10_raw: str
    icd10_codes: list[str] = field(default_factory=list)
    icd10_primary: str = ""
    chapter_roman: str = ""
    chapter_title: str = ""
    chapter_range: str = ""
    severity: Optional[int] = None
    is_severe: bool = False

    def as_row(self) -> dict[str, object]:
        return {
            "disease": self.disease,
            "icd10_raw": self.icd10_raw,
            "icd10_codes": "|".join(self.icd10_codes),
            "icd10_primary": self.icd10_primary,
            "chapter_roman": self.chapter_roman,
            "chapter_title": self.chapter_title,
            "chapter_range": self.chapter_range,
            "severity": self.severity if self.severity is not None else "",
            "is_severe": int(self.is_severe),
        }


def normalise_codes(raw: str) -> list[str]:
    """Split a raw ICD-10 string into trimmed, upper-cased codes."""
    if not raw:
        return []
    return [token.strip().upper() for token in raw.split(",") if token.strip()]


def lookup_chapter(code: str) -> Optional[Chapter]:
    """Resolve a code to its ICD-10 chapter using inclusive numeric ranges."""
    code = code.strip().upper()
    if not code:
        return None
    letter = code[0]
    digits = ""
    for char in code[1:]:
        if char.isdigit():
            digits += char
        else:
            break
        if len(digits) == 2:
            break
    number = int(digits) if digits else 0
    key = _bound(letter, number)
    for chapter in CHAPTERS:
        if chapter.contains(key):
            return chapter
    return None


def choose_primary(codes: list[str]) -> str:
    """Pick the canonical ICD-10 identifier for a (possibly multi-code) entry."""
    if not codes:
        return ""
    override = CANONICAL_OVERRIDES.get(tuple(codes))
    return override if override else codes[0]


def _condition_name(key: str, record: dict) -> str:
    for field_name in ("cond-name-eng", "condition_name", "cond_name_eng"):
        value = record.get(field_name)
        if value:
            return str(value)
    return key


def build_references(conditions: dict) -> list[ConditionReference]:
    """Transform the raw condition catalogue into reviewable reference rows."""
    references: list[ConditionReference] = []
    for key, record in conditions.items():
        if not isinstance(record, dict):
            LOGGER.warning("Skipping non-object entry: %s", key)
            continue
        raw = str(record.get("icd10-id", record.get("icd10_id", "")) or "")
        codes = normalise_codes(raw)
        primary = choose_primary(codes)
        chapter = lookup_chapter(primary)
        if chapter is None and primary:
            LOGGER.warning("No ICD-10 chapter matched for %s (%s)", key, primary)
        severity_raw = record.get("severity")
        severity = int(severity_raw) if severity_raw is not None else None
        references.append(
            ConditionReference(
                disease=_condition_name(key, record),
                icd10_raw=raw,
                icd10_codes=codes,
                icd10_primary=primary,
                chapter_roman=chapter.roman if chapter else "",
                chapter_title=chapter.title if chapter else "",
                chapter_range=chapter.code_range if chapter else "",
                severity=severity,
                is_severe=severity is not None and severity <= SEVERE_THRESHOLD,
            )
        )
    references.sort(key=lambda ref: ref.disease.lower())
    return references


def write_csv(references: Iterable[ConditionReference], path: Path) -> None:
    references = list(references)
    fieldnames = list(references[0].as_row().keys()) if references else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for ref in references:
            writer.writerow(ref.as_row())
    LOGGER.info("Wrote %d rows to %s", len(references), path)


def write_markdown(references: list[ConditionReference], path: Path) -> None:
    severity_dist = Counter(
        ref.severity for ref in references if ref.severity is not None
    )
    severe = [ref for ref in references if ref.is_severe]
    multi_code = [ref for ref in references if len(ref.icd10_codes) > 1]

    lines: list[str] = []
    lines.append("# ICD-10 & Severity Reference — DDXPlus Knowledge Base")
    lines.append("")
    lines.append("**Project:** Disease-Diagnosis-RAG-System — AIO 2026, Project 1  ")
    lines.append("**Team:** Med / Pharm / Bio Nexus  ")
    lines.append("**Author:** Nguyễn Văn Thương (Team Leader — Domain Expert)  ")
    lines.append("**Generated:** 2026-06-12  ")
    lines.append("**Source:** `release_conditions.json` (DDXPlus, CC-BY)")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("- ICD-10 codes are taken verbatim from the source, then trimmed and upper-cased.")
    lines.append("- Chapters are assigned by official numeric ranges, not by leading letter.")
    lines.append("- For the single multi-code condition, the canonical `doc_id` is pinned")
    lines.append("  explicitly (see `CANONICAL_OVERRIDES`); all codes are retained.")
    lines.append(f"- A condition is flagged severe when `severity <= {SEVERE_THRESHOLD}` (1 = most severe).")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total conditions: **{len(references)}**")
    dist_str = " · ".join(f"sev {sev} = {severity_dist.get(sev, 0)}" for sev in (1, 2, 3, 4, 5))
    lines.append(f"- Severity distribution: {dist_str}")
    lines.append(f"- Severe conditions (severity ≤ {SEVERE_THRESHOLD}): **{len(severe)}**")
    lines.append(f"- Multi-code conditions: **{len(multi_code)}**")
    lines.append("")
    lines.append("## Reference table")
    lines.append("")
    lines.append("| Disease | ICD-10 (raw) | Primary | Chapter | Range | Severity | Severe |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for ref in references:
        severe_mark = "✅" if ref.is_severe else ""
        severity = ref.severity if ref.severity is not None else ""
        lines.append(
            f"| {ref.disease} | {ref.icd10_raw} | {ref.icd10_primary} | "
            f"{ref.chapter_roman} | {ref.chapter_range} | {severity} | {severe_mark} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    LOGGER.info("Wrote Markdown audit to %s", path)


def load_conditions(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object keyed by condition name.")
    return data


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--conditions", type=Path, default=Path("release_conditions.json"), help="Path to release_conditions.json")
    parser.add_argument("--outdir", type=Path, default=Path("."), help="Output directory")
    parser.add_argument("--prefix", default="icd10_audit", help="Output file name prefix")
    parser.add_argument("--expected", type=int, default=None, help="Expected condition count for validation")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if not args.conditions.exists():
        LOGGER.error("Source not found: %s", args.conditions)
        return 1

    conditions = load_conditions(args.conditions)
    references = build_references(conditions)

    if args.expected is not None and len(references) != args.expected:
        LOGGER.warning("Expected %d conditions, found %d", args.expected, len(references))

    args.outdir.mkdir(parents=True, exist_ok=True)
    write_csv(references, args.outdir / f"{args.prefix}.csv")
    write_markdown(references, args.outdir / f"{args.prefix}.md")
    LOGGER.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
