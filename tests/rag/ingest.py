"""Unit tests for src.services.rag.ingest.Ingestion."""

import json
from pathlib import Path
from unittest.mock import Mock

from src.services.rag.ingest import Ingestion
from src.services.rag.pipeline import RAGService
from src.services.rag.preprocess import (
    build_description,
    build_embed_text,
    normalize_symptom_phrase,
)
from src.services.rag.schemas import DiseaseDocument

KB_PATH = Path("data/kb/kb_ddxplus.json")
RAWQ_PATH = Path("data/kb/kb_ddxplus_rawq.json")

INDEX_TEXT_FIELDS = (
    "doc_id",
    "disease",
    "symptoms",
    "antecedents",
    "severity",
    "description",
    "source",
    "keyword_text",
)


def _dedup_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _load_kb_rows() -> dict[str, dict]:
    return {
        row["doc_id"]: row for row in json.loads(KB_PATH.read_text(encoding="utf-8"))
    }


def _load_rawq_rows() -> dict[str, dict]:
    return {
        row["doc_id"]: row for row in json.loads(RAWQ_PATH.read_text(encoding="utf-8"))
    }


def _build_document_from_raw_questions(
    raw_row: dict, ingestion: Ingestion
) -> DiseaseDocument:
    symptoms = _dedup_keep_order(
        [normalize_symptom_phrase(s) for s in raw_row["symptoms"]]
    )
    antecedents = _dedup_keep_order(
        [normalize_symptom_phrase(a) for a in raw_row["antecedents"]]
    )
    doc = DiseaseDocument(
        doc_id=raw_row["doc_id"],
        disease=raw_row["disease"],
        symptoms=symptoms,
        antecedents=antecedents,
        severity=raw_row["severity"],
        description=build_description(symptoms, antecedents),
        source=raw_row["source"],
    )
    return ingestion._normalize_record(doc)


def test_ingest_returns_zero_for_empty_records(
    ingestion: Ingestion,
) -> None:
    assert ingestion.ingest([]) == 0


def test_ingest_embeds_and_bulk_indexes_documents(
    ingestion: Ingestion,
    sample_disease_document: DiseaseDocument,
    mock_ingest_embed_service: Mock,
    mock_bulk_client: Mock,
) -> None:
    count = ingestion.ingest([sample_disease_document])

    assert count == 1

    mock_ingest_embed_service.embed_documents.assert_called_once()

    mock_bulk_client.bulk.assert_called_once()


def test_ingest_builds_expected_embedding_text(
    ingestion: Ingestion,
    sample_disease_document: DiseaseDocument,
    mock_ingest_embed_service: Mock,
) -> None:
    ingestion.ingest([sample_disease_document])

    embed_texts = mock_ingest_embed_service.embed_documents.call_args.args[0]

    assert len(embed_texts) == 1

    assert embed_texts[0] == (
        "Disease: Influenza. Symptoms: fever, cough. Antecedents: ."
    )


def test_ingest_creates_expected_bulk_action(
    ingestion: Ingestion,
    sample_disease_document: DiseaseDocument,
    mock_bulk_client: Mock,
) -> None:
    ingestion.ingest([sample_disease_document])

    actions = mock_bulk_client.bulk.call_args.args[0]

    assert len(actions) == 1

    action = actions[0]

    assert action["_id"] == "doc-1"
    assert action["disease"] == "Influenza"
    assert action["keyword_text"] == "Influenza fever cough"
    assert action["severity"] == 2
    assert action["source"] == "ddxplus"


def test_ingest_normalizes_symptoms(
    ingestion: Ingestion,
    mock_bulk_client: Mock,
) -> None:
    record = DiseaseDocument(
        doc_id="doc-2",
        disease="Influenza",
        symptoms=["Fever", "COUGH"],
        severity=2,
        source="ddxplus",
    )

    ingestion.ingest([record])

    action = mock_bulk_client.bulk.call_args.args[0][0]
    assert action["symptoms"] == ["fever", "cough"]
    assert action["keyword_text"] == "Influenza fever cough"


def test_ingest_batches_large_record_lists(
    mock_ingest_embed_service: Mock,
    mock_bulk_client: Mock,
) -> None:
    mock_ingest_embed_service.embed_documents.side_effect = lambda texts: [
        [0.1] * 384 for _ in texts
    ]
    ingestion = Ingestion(
        embed_service=mock_ingest_embed_service,
        client=mock_bulk_client,
        batch_size=2,
    )
    records = [
        DiseaseDocument(
            doc_id=f"doc-{index}",
            disease="Influenza",
            symptoms=["fever"],
            severity=2,
            source="ddxplus",
        )
        for index in range(5)
    ]

    count = ingestion.ingest(records)

    assert count == 5
    assert mock_bulk_client.bulk.call_count == 3
    assert mock_ingest_embed_service.embed_documents.call_count == 3


def test_disease_document_embed_text() -> None:
    record = DiseaseDocument(
        doc_id="doc-1",
        disease="Influenza",
        symptoms=["fever", "cough"],
        antecedents=["smoking"],
        severity=2,
        source="ddxplus",
        description="Example disease",
    )

    assert record.embed_text == (
        "Disease: Influenza. Symptoms: fever, cough. Antecedents: smoking."
    )


def test_disease_document_keyword_text() -> None:
    record = DiseaseDocument(
        doc_id="doc-1",
        disease="Influenza",
        symptoms=["fever", "cough"],
        antecedents=["autoimmune disease"],
        severity=2,
        source="ddxplus",
    )

    assert record.keyword_text == "Influenza fever cough autoimmune disease"


def test_raw_questions_produce_kb_document_shape_and_text_fields(
    ingestion: Ingestion,
) -> None:
    """Raw DDXPlus questions (rawq) -> src pipeline must match kb_ddxplus.json."""
    expected = _load_kb_rows()
    rawq = _load_rawq_rows()

    assert len(expected) == 49
    assert set(expected) == set(rawq)

    for doc_id, kb_row in expected.items():
        doc = _build_document_from_raw_questions(rawq[doc_id], ingestion)
        payload = doc.to_dict()
        payload["keyword_text"] = doc.keyword_text

        for field in INDEX_TEXT_FIELDS:
            assert payload[field] == kb_row[field], doc_id

        assert doc.embed_text == build_embed_text(
            kb_row["disease"], kb_row["symptoms"], kb_row["antecedents"]
        )


def test_kb_roundtrip_through_ragservice_preserves_text_fields(
    mock_ingest_embed_service: Mock,
    mock_bulk_client: Mock,
) -> None:
    """kb_ddxplus.json -> RAGService.ingestion must preserve all index text fields."""
    service = RAGService(
        client=mock_bulk_client,
        embed_service=mock_ingest_embed_service,
        rerank_service=Mock(),
    )
    kb_rows = _load_kb_rows().values()

    for kb_row in kb_rows:
        doc = DiseaseDocument(
            doc_id=kb_row["doc_id"],
            disease=kb_row["disease"],
            symptoms=kb_row["symptoms"],
            antecedents=kb_row["antecedents"],
            severity=kb_row["severity"],
            description=kb_row["description"],
            source=kb_row["source"],
        )
        normalized = service.ingestion._normalize_record(doc)

        for field in INDEX_TEXT_FIELDS:
            got = (
                normalized.keyword_text
                if field == "keyword_text"
                else getattr(normalized, field)
            )
            assert got == kb_row[field], kb_row["doc_id"]


def test_ingest_bulk_action_shape_matches_index_mapping(
    ingestion: Ingestion,
    mock_ingest_embed_service: Mock,
    mock_bulk_client: Mock,
) -> None:
    """Bulk payload keys must match ddxplus index fields (doc_id is OpenSearch _id)."""
    kb_row = next(iter(_load_kb_rows().values()))
    doc = DiseaseDocument(
        doc_id=kb_row["doc_id"],
        disease=kb_row["disease"],
        symptoms=kb_row["symptoms"],
        antecedents=kb_row["antecedents"],
        severity=kb_row["severity"],
        description=kb_row["description"],
        source=kb_row["source"],
    )

    ingestion.ingest([doc])

    action = mock_bulk_client.bulk.call_args.args[0][0]
    assert action["_id"] == kb_row["doc_id"]
    assert set(action.keys()) == {
        "_index",
        "_id",
        "doc_id",
        "disease",
        "symptoms",
        "antecedents",
        "severity",
        "description",
        "source",
        "keyword_text",
        "embedding",
    }
    assert "icd10_codes" not in action
    assert action["keyword_text"] == kb_row["keyword_text"]
