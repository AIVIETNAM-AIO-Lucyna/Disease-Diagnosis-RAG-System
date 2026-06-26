"""Preprocessing for DDXPlus KB build, ingest, and retrieval query paths."""

from __future__ import annotations

import re

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
    r"^do you have a known\b",
    r"^do you have any\b",
    r"^do you have an\b",
    r"^do you have\b",
    r"^do you feel\b",
    r"^do you ever\b",
    r"^did you previously,? or do you currently,? have any\b",
    r"^did you\b",
    r"^have you ever been diagnosed with\b",
    r"^have you ever had\b",
    r"^have you ever felt like you were\b",
    r"^have you ever\b",
    r"^have you recently had\b",
    r"^have you recently\b",
    r"^have you noticed any\b",
    r"^have you started or taken any\b",
    r"^are you experiencing\b",
    r"^are you feeling\b",
    r"^are you consulting because you have\b",
    r"^do you currently,? or did you ever,? have\b",
    r"^do you currently take\b",
    r"^do you take a\b",
    r"^do you take\b",
    r"^do you suffer from\b",
    r"^do you feel that\b",
    r"^do you feel like\b",
    r"^do you think you are\b",
    r"^have you had a\b",
    r"^have you had one or several\b",
    r"^have you had\b",
    r"^have you been\b",
    r"^have you noticed\b",
    r"^have any of your\b",
    r"^were you diagnosed with\b",
    r"^were you\b",
    r"^are you currently taking or have you recently taken\b",
    r"^are you currently\b",
    r"^are you\b",
    r"^is the\b",
    r"^is your\b",
    r"^how\b",
    r"^characterize your\b",
    r"^what\b",
    r"^where\b",
    r"^do you\b",
]

SYMPTOM_SYNONYMS: dict[str, str] = {
    "tired": "fatigue",
    "exhausted": "fatigue",
    "throwing up": "vomiting",
    "threw up": "vomiting",
    "high fever": "high fever",
    "skin rash": "skin rash",
}

CANONICAL_DOC_ID_OVERRIDES: dict[tuple[str, ...], str] = {
    ("J17", "J18"): "J18",
}


def normalize_symptom(token: str) -> str:
    """Normalize a symptom token by removing underscores and replacing multiple spaces with a single space."""
    cleaned = token.strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", cleaned)


def normalize_symptoms(symptoms: list[str]) -> list[str]:
    """Normalize a list of symptoms by removing duplicates and normalizing each symptom."""
    seen: set[str] = set()
    normalized: list[str] = []
    for symptom in symptoms:
        value = normalize_symptom(symptom)
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def normalize_symptom_phrase(question: str) -> str:
    """Normalize a symptom phrase by removing parentheses, trailing punctuation, and leading frames."""
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
        r"\b(?:,?\s*(?:or|and)\s+(?:do|did|have|has|are|were|is)\s+(?:you|your))\b",
        s,
    )[0]
    s = re.sub(r"^(been|had|a|an|the|any|with|that|to)\b\s*", "", s).strip()
    s = re.sub(r"\s+", " ", s).strip(" ,;:")
    return s or question.strip().lower()


def normalize_icd10(code: str) -> str:
    """Normalize an ICD-10 code by stripping whitespace and converting to uppercase."""
    return (code or "").strip().upper()


def split_icd10_codes(raw: str) -> list[str]:
    """Split an ICD-10 code string into a list of normalized codes."""
    return [normalize_icd10(c) for c in str(raw or "").split(",") if c.strip()]


def choose_canonical_doc_id(codes: list[str]) -> str:
    """Choose a canonical ICD-10 code from a list of codes."""
    if not codes:
        return ""
    key = tuple(sorted(codes))
    return CANONICAL_DOC_ID_OVERRIDES.get(key, codes[0])


def build_keyword_text(
    disease: str, symptoms: list[str], antecedents: list[str]
) -> str:
    """Build a keyword text from a disease, symptoms, and antecedents."""
    return " ".join([disease, *symptoms, *antecedents])


def build_embed_text(disease: str, symptoms: list[str], antecedents: list[str]) -> str:
    """Build an embed text from a disease, symptoms, and antecedents."""
    symptom_str = ", ".join(symptoms)
    antecedent_str = ", ".join(antecedents)
    return (
        f"Disease: {disease}. Symptoms: {symptom_str}. Antecedents: {antecedent_str}."
    )


def build_description(symptoms: list[str], antecedents: list[str]) -> str:
    """Build a description from a list of symptoms and antecedents."""
    desc = f"Condition characterized by: {', '.join(symptoms)}."
    if antecedents:
        desc += f" Risk factors: {', '.join(antecedents)}."
    return desc


class PreprocessPipeline:
    """Query preprocessing for production retrieval and DDXPlus evidence build.

    Production ``RAGService.query()`` uses **synonym expansion + per-token normalize**
    only. ``normalize_symptom_phrase`` strips DDXPlus question frames and is meant
    for single evidence strings at KB / EXP-02 eval build time — not whole free-text
    user queries (multi-symptom prose would be mangled by lead-frame regexes).
    """

    def expand_synonyms(self, text: str) -> str:
        """Expand synonyms in a text."""
        expanded = text.lower()
        for source, target in sorted(
            SYMPTOM_SYNONYMS.items(), key=lambda item: -len(item[0])
        ):
            expanded = expanded.replace(source, normalize_symptom(target))
        return expanded

    def preprocess_ddxplus_evidence(self, question: str) -> str:
        """Normalize one DDXPlus evidence question (KB build, offline/live eval queries)."""
        return normalize_symptom_phrase(self.expand_synonyms(question))

    def preprocess_query(self, query: str) -> str:
        """Free-text production path: synonyms, then token-level symptom normalize."""
        expanded = self.expand_synonyms(query)
        tokens: list[str] = []
        for token in re.split(r"[,;\n]+|\s+", expanded):
            cleaned = token.strip().strip("?.!").strip()
            if cleaned:
                tokens.append(cleaned)
        return " ".join(normalize_symptoms(tokens))
