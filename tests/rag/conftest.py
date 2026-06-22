"""Fixtures for RAG service-layer unit tests."""

from typing import Any
from unittest.mock import Mock

import pytest

from src.schemas import SearchResponse
from src.services.rag.retrieve import Retriever
from src.settings import settings

from src.services.rag.ingest import Ingestion
from src.services.rag.schemas import IngestRecord


def fake_embedding(dim: int = settings.EMBEDDING_DIM) -> list[float]:
    return [0.1] * dim


def knn_vector_from_search_body(body: dict[str, Any]) -> list[float]:
    """Extract the k-NN vector from a vector or hybrid search body."""
    query = body["query"]
    if "knn" in query:
        return query["knn"]["embedding"]["vector"]
    return query["hybrid"]["queries"][1]["knn"]["embedding"]["vector"]


def make_search_response(
    *,
    took: int = 12,
    total: int = 1,
    hits: list[dict[str, Any]] | None = None,
) -> SearchResponse:
    if hits is None:
        hits = [
            {
                "_index": "diseases",
                "_id": "G70.0",
                "_score": 1.42,
                "_source": {
                    "doc_id": "G70.0",
                    "disease": "Myasthenia gravis",
                    "symptoms": ["fatigue", "muscle weakness"],
                    "antecedents": ["autoimmune disease"],
                    "severity": 1,
                    "description": "Example description",
                    "source": "ddxplus",
                },
            }
        ]

    return SearchResponse.model_validate(
        {
            "took": took,
            "timed_out": False,
            "_shards": {
                "total": 1,
                "successful": 1,
                "skipped": 0,
                "failed": 0,
            },
            "hits": {
                "total": {"value": total, "relation": "eq"},
                "max_score": hits[0]["_score"] if hits else None,
                "hits": hits,
            },
        }
    )


@pytest.fixture
def mock_embed_service() -> Mock:
    service = Mock()
    service.embed_query.return_value = fake_embedding()
    return service


@pytest.fixture
def mock_opensearch_client() -> Mock:
    client = Mock()
    client.query.return_value = make_search_response()
    return client


@pytest.fixture
def retriever(mock_embed_service: Mock, mock_opensearch_client: Mock) -> Retriever:
    return Retriever(
        embed_service=mock_embed_service,
        client=mock_opensearch_client,
    )


@pytest.fixture
def sample_ingest_record() -> IngestRecord:
    return IngestRecord(
        doc_id="doc-1",
        disease="Influenza",
        symptoms=["fever", "cough"],
        keyword_text="influenza fever cough",
        severity=2,
        source="ddxplus",
        antecedents=[],
        description="Example disease",
    )


@pytest.fixture
def mock_bulk_client() -> Mock:
    client = Mock()
    client.bulk.return_value = None
    return client


@pytest.fixture
def mock_ingest_embed_service() -> Mock:
    service = Mock()
    service.embed_documents.return_value = [
        fake_embedding(),
    ]
    return service


@pytest.fixture
def ingestion(
    mock_ingest_embed_service: Mock,
    mock_bulk_client: Mock,
) -> Ingestion:
    return Ingestion(
        embed_service=mock_ingest_embed_service,
        client=mock_bulk_client,
    )
