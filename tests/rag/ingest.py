"""Unit tests for src.services.rag.ingest.Ingestion."""

from unittest.mock import Mock

from src.services.rag.ingest import Ingestion
from src.services.rag.schemas import IngestRecord


def test_ingest_returns_zero_for_empty_records(
    ingestion: Ingestion,
) -> None:
    assert ingestion.ingest([]) == 0

def test_ingest_embeds_and_bulk_indexes_documents(
    ingestion: Ingestion,
    sample_ingest_record: IngestRecord,
    mock_ingest_embed_service: Mock,
    mock_bulk_client: Mock,
) -> None:
    count = ingestion.ingest([sample_ingest_record])

    assert count == 1

    mock_ingest_embed_service.embed_documents.assert_called_once()

    mock_bulk_client.bulk.assert_called_once()

def test_ingest_builds_expected_embedding_text(
    ingestion: Ingestion,
    sample_ingest_record: IngestRecord,
    mock_ingest_embed_service: Mock,
) -> None:
    ingestion.ingest([sample_ingest_record])

    embed_texts = (
        mock_ingest_embed_service.embed_documents.call_args.args[0]
    )

    assert len(embed_texts) == 1

    assert embed_texts[0] == (
        "Disease: Influenza. "
        "Symptoms: fever, cough. "
        "Example disease"
    )

def test_ingest_creates_expected_bulk_action(
    ingestion: Ingestion,
    sample_ingest_record: IngestRecord,
    mock_bulk_client: Mock,
) -> None:
    ingestion.ingest([sample_ingest_record])

    actions = mock_bulk_client.bulk.call_args.args[0]

    assert len(actions) == 1

    action = actions[0]

    assert action["_id"] == "doc-1"
    assert action["disease"] == "Influenza"
    assert action["severity"] == 2
    assert action["source"] == "ddxplus"

def test_build_embed_text() -> None:
    text = Ingestion._build_embed_text(
        disease="Influenza",
        symptoms=["fever", "cough"],
        description="Example disease",
    )

    assert text == (
        "Disease: Influenza. "
        "Symptoms: fever, cough. "
        "Example disease"
    )
