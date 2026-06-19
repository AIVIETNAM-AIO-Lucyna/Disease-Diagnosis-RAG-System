"""Fixtures for RAG service-layer unit tests."""

from typing import Any
from unittest.mock import Mock

import pytest

from src.schemas import SearchResponse
from src.services.rag.retrieve import Retriever
from src.settings import settings


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
