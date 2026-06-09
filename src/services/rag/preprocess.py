"""Query and symptom normalization for retrieval and ingest."""

import re

# MVP synonym map: user-facing phrase -> canonical symptom token
SYMPTOM_SYNONYMS: dict[str, str] = {
    "tired": "fatigue",
    "exhausted": "fatigue",
    "throwing up": "vomiting",
    "threw up": "vomiting",
    "high fever": "high fever",
    "skin rash": "skin rash",
}


def normalize_symptom(token: str) -> str:
    """Normalize a single symptom token (ingest + query)."""
    cleaned = token.strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", cleaned)


def normalize_symptoms(symptoms: list[str]) -> list[str]:
    """Normalize symptom tokens, preserving order and uniqueness."""
    seen: set[str] = set()
    normalized: list[str] = []
    for symptom in symptoms:
        value = normalize_symptom(symptom)
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def expand_synonyms(text: str) -> str:
    """Replace known synonym phrases in free-text queries."""
    expanded = text.lower()
    for source, target in sorted(SYMPTOM_SYNONYMS.items(), key=lambda item: -len(item[0])):
        expanded = expanded.replace(source, normalize_symptom(target))
    return expanded


def preprocess_query(query: str) -> str:
    """Normalize and expand a user symptom query before retrieval."""
    expanded = expand_synonyms(query)
    tokens = re.split(r"[,;\n]+|\s+", expanded)
    normalized = normalize_symptoms([token for token in tokens if token.strip()])
    return " ".join(normalized)
