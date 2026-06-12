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
