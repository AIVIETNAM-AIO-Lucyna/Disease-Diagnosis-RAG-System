"""Unit tests for src.services.rag.ingest.Ingestion."""

from unittest.mock import Mock

from src.services.rag.ingest import Ingestion
from src.services.rag.schemas import DiseaseDocument


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
        "Disease: Influenza. "
        "Symptoms: fever, cough. "
        "Example disease"
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
    mock_ingest_embed_service.embed_documents.side_effect = (
        lambda texts: [[0.1] * 384 for _ in texts]
    )
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
        severity=2,
        source="ddxplus",
        description="Example disease",
    )

    assert record.embed_text == (
        "Disease: Influenza. "
        "Symptoms: fever, cough. "
        "Example disease"
    )


def test_disease_document_keyword_text() -> None:
    record = DiseaseDocument(
        doc_id="doc-1",
        disease="Influenza",
        symptoms=["Fever", "COUGH"],
        antecedents=["Autoimmune Disease"],
        severity=2,
        source="ddxplus",
    )

    assert record.keyword_text == "Influenza fever cough autoimmune disease"
