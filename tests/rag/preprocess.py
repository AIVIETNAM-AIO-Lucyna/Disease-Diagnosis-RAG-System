"""Unit tests for src.services.rag.preprocess."""

from src.services.rag.preprocess import (
    PreprocessPipeline,
    normalize_symptom_phrase,
)


def test_preprocess_query_expands_synonyms_and_normalizes_tokens() -> None:
    pipeline = PreprocessPipeline()
    assert (
        pipeline.preprocess_query("I am tired, have fever") == "i am fatigue have fever"
    )


def test_preprocess_ddxplus_evidence_strips_question_frames() -> None:
    pipeline = PreprocessPipeline()
    assert pipeline.preprocess_ddxplus_evidence("Do you have a cough?") == "cough"


def test_normalize_symptom_phrase_matches_kb_build() -> None:
    assert (
        normalize_symptom_phrase(
            "Do you have a fever (either felt or measured with a thermometer)?"
        )
        == "fever"
    )
