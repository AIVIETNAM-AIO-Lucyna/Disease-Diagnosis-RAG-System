"""Unit tests for ``src.services.rag.retrieve.Retriever``."""

from typing import Any
from unittest.mock import Mock

import pytest

from src.schemas import SearchResponse
from src.services.rag.retrieve import Retriever
from src.services.rag.schemas import (
    Bm25RetrieveRequest,
    HybridRetrieveRequest,
    RetrievalMode,
    RetrieveExperimentRequest,
    VectorRetrieveRequest,
)
from src.settings import settings
from tests.rag.conftest import (
    fake_embedding,
    knn_vector_from_search_body,
    make_search_response,
)


class TestRetrieverHelpers:
    def test_build_hits_maps_source_fields(self) -> None:
        response = make_search_response()

        hits = Retriever._build_hits(response)

        assert len(hits) == 1
        hit = hits[0]
        assert hit.rank == 1
        assert hit.score == 1.42
        assert hit.doc_id == "G70.0"
        assert hit.disease == "Myasthenia gravis"
        assert hit.symptoms == ["fatigue", "muscle weakness"]
        assert hit.antecedents == ["autoimmune disease"]
        assert hit.severity == 1
        assert hit.description == "Example description"
        assert hit.source == "ddxplus"

    def test_build_hits_handles_missing_source(self) -> None:
        response = make_search_response(
            hits=[{"_index": "diseases", "_id": "x", "_score": 0.5, "_source": None}]
        )

        hits = Retriever._build_hits(response)

        assert hits[0].doc_id is None
        assert hits[0].disease is None

    @pytest.mark.parametrize(
        ("total", "expected"),
        [
            ({"value": 7, "relation": "eq"}, 7),
            (3, 3),
        ],
    )
    def test_total_hits(self, total: dict[str, Any] | int, expected: int) -> None:
        response = SearchResponse.model_validate(
            {
                "took": 1,
                "timed_out": False,
                "_shards": {
                    "total": 1,
                    "successful": 1,
                    "skipped": 0,
                    "failed": 0,
                },
                "hits": {"total": total, "hits": []},
            }
        )

        assert Retriever._total_hits(response) == expected

    def test_to_retrieve_result(self) -> None:
        response = make_search_response(took=99)

        result = Retriever._to_retrieve_result(response)

        assert result.took_ms == 99
        assert len(result.hits) == 1
        assert result.hits[0].doc_id == "G70.0"

    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            (RetrievalMode.BM25, RetrievalMode.BM25),
            ("knn", RetrievalMode.KNN),
        ],
    )
    def test_normalize_mode(
        self, mode: RetrievalMode | str, expected: RetrievalMode
    ) -> None:
        assert Retriever._normalize_mode(mode) == expected

    def test_to_experiment_mode_result_includes_total_hits(self) -> None:
        response = make_search_response(took=42, total=7)

        result = Retriever._to_experiment_mode_result(
            mode=RetrievalMode.BM25,
            response=response,
        )

        assert result.mode == RetrievalMode.BM25
        assert result.took_ms == 42
        assert result.total_hits == 7
        assert len(result.hits) == 1


class TestRetrieveRequestSchemas:
    def test_vector_to_search_body_requires_embedding(self) -> None:
        request = VectorRetrieveRequest(query="fever")

        with pytest.raises(ValueError, match="embedding must be set"):
            request.to_search_body()

    def test_hybrid_to_search_body_requires_embedding(self) -> None:
        request = HybridRetrieveRequest(query="fever")

        with pytest.raises(ValueError, match="embedding must be set"):
            request.to_search_body()


class TestRetrieverSearch:
    def test_search_bm25_queries_opensearch_and_returns_hits(
        self,
        retriever: Retriever,
        mock_opensearch_client: Mock,
    ) -> None:
        request = Bm25RetrieveRequest(query="fatigue cough", index_name="diseases")

        result = retriever.search_bm25(request)

        mock_opensearch_client.query.assert_called_once()
        index_name, body = mock_opensearch_client.query.call_args.args
        assert index_name == "diseases"
        assert body["query"]["match"]["keyword_text"]["query"] == "fatigue cough"
        assert len(result.hits) == 1

    def test_search_bm25_preprocesses_query_by_default(
        self,
        retriever: Retriever,
        mock_opensearch_client: Mock,
    ) -> None:
        request = Bm25RetrieveRequest(query="I am tired")

        retriever.search_bm25(request)

        body = mock_opensearch_client.query.call_args.args[1]
        assert body["query"]["match"]["keyword_text"]["query"] == "i am fatigue"

    def test_search_bm25_skips_preprocess_when_disabled(
        self,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        retriever = Retriever(
            embed_service=mock_embed_service,
            client=mock_opensearch_client,
            preprocess=False,
        )
        request = Bm25RetrieveRequest(query="I am tired")

        retriever.search_bm25(request)

        body = mock_opensearch_client.query.call_args.args[1]
        assert body["query"]["match"]["keyword_text"]["query"] == "I am tired"

    def test_search_vector_embeds_query_when_embedding_omitted(
        self,
        retriever: Retriever,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        request = VectorRetrieveRequest(query="fever cough")

        result = retriever.search_vector(request)

        mock_embed_service.embed_query.assert_called_once_with("fever cough")
        body = mock_opensearch_client.query.call_args.args[1]
        assert knn_vector_from_search_body(body) == fake_embedding()
        assert len(result.hits) == 1

    def test_search_vector_uses_provided_embedding(
        self,
        retriever: Retriever,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        embedding = fake_embedding()
        request = VectorRetrieveRequest(query="fever cough", embedding=embedding)

        retriever.search_vector(request)

        mock_embed_service.embed_query.assert_not_called()
        body = mock_opensearch_client.query.call_args.args[1]
        assert knn_vector_from_search_body(body) == embedding

    def test_search_hybrid_embeds_query_when_embedding_omitted(
        self,
        retriever: Retriever,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        request = HybridRetrieveRequest(query="fever cough")

        retriever.search_hybrid(request)

        mock_embed_service.embed_query.assert_called_once_with("fever cough")
        body = mock_opensearch_client.query.call_args.args[1]
        assert knn_vector_from_search_body(body) == fake_embedding()

    def test_search_hybrid_passes_search_pipeline(
        self,
        retriever: Retriever,
        mock_opensearch_client: Mock,
    ) -> None:
        request = HybridRetrieveRequest(
            query="fever",
            search_pipeline="hybrid-rrf",
        )

        retriever.search_hybrid(request)

        mock_opensearch_client.query.assert_called_once()
        _, kwargs = mock_opensearch_client.query.call_args
        assert kwargs["search_pipeline"] == "hybrid-rrf"

    def test_retrieve_delegates_to_hybrid_with_default_index(
        self,
        retriever: Retriever,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        result = retriever.retrieve("fever cough")

        index_name = mock_opensearch_client.query.call_args.args[0]
        assert index_name == settings.RETRIEVE_INDEX_ALIAS
        mock_embed_service.embed_query.assert_called_once_with("fever cough")
        assert len(result.hits) == 1


class TestRetrieverExperiment:
    def test_run_experiment_runs_requested_modes(
        self,
        retriever: Retriever,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        mock_opensearch_client.query.side_effect = [
            make_search_response(took=10, total=3),
            make_search_response(took=20, total=5),
            make_search_response(took=30, total=7),
        ]
        request = RetrieveExperimentRequest(
            query="fever",
            modes=[RetrievalMode.BM25, RetrievalMode.KNN, RetrievalMode.HYBRID],
            include_opensearch_body=True,
        )

        response = retriever.run_experiment(request)

        assert mock_opensearch_client.query.call_count == 3
        assert mock_embed_service.embed_query.call_count == 1
        assert set(response.results.keys()) == {
            RetrievalMode.BM25,
            RetrievalMode.KNN,
            RetrievalMode.HYBRID,
        }
        assert response.results[RetrievalMode.BM25].mode == RetrievalMode.BM25
        assert response.results[RetrievalMode.BM25].took_ms == 10
        assert response.results[RetrievalMode.BM25].total_hits == 3
        assert response.results[RetrievalMode.KNN].took_ms == 20
        assert response.results[RetrievalMode.HYBRID].took_ms == 30
        assert (
            response.results[RetrievalMode.HYBRID].search_pipeline
            == settings.CURRENT_SEARCH_PIPELINE
        )
        assert response.results[RetrievalMode.BM25].opensearch_body is not None
        assert response.modes_run == ["bm25", "knn", "hybrid"]

    def test_run_experiment_excludes_opensearch_body_by_default(
        self,
        retriever: Retriever,
    ) -> None:
        request = RetrieveExperimentRequest(
            query="fever",
            modes=[RetrievalMode.BM25],
        )

        response = retriever.run_experiment(request)

        assert response.results[RetrievalMode.BM25].opensearch_body is None

    def test_run_experiment_preprocesses_query(
        self,
        retriever: Retriever,
        mock_opensearch_client: Mock,
    ) -> None:
        request = RetrieveExperimentRequest(
            query="I am tired",
            modes=[RetrievalMode.BM25],
        )

        response = retriever.run_experiment(request)

        body = mock_opensearch_client.query.call_args.args[1]
        assert body["query"]["match"]["keyword_text"]["query"] == "i am fatigue"
        assert response.query == "i am fatigue"

    def test_run_experiment_bm25_only_skips_embedding(
        self,
        retriever: Retriever,
        mock_embed_service: Mock,
    ) -> None:
        request = RetrieveExperimentRequest(
            query="fever",
            modes=[RetrievalMode.BM25],
        )

        retriever.run_experiment(request)

        mock_embed_service.embed_query.assert_not_called()

    def test_run_experiment_sets_embedding_once_for_vector_modes(
        self,
        retriever: Retriever,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        mock_opensearch_client.query.side_effect = [
            make_search_response(took=10),
            make_search_response(took=20),
        ]
        request = RetrieveExperimentRequest(
            query="fever",
            modes=[RetrievalMode.KNN, RetrievalMode.HYBRID],
        )

        retriever.run_experiment(request)

        mock_embed_service.embed_query.assert_called_once_with("fever")
        for call in mock_opensearch_client.query.call_args_list:
            assert knn_vector_from_search_body(call.args[1]) == fake_embedding()

    def test_run_experiment_uses_fixed_embedding(
        self,
        retriever: Retriever,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        embedding = fake_embedding()
        request = RetrieveExperimentRequest(
            query="fever",
            modes=[RetrievalMode.KNN, RetrievalMode.HYBRID],
            embedding=embedding,
        )

        retriever.run_experiment(request)

        mock_embed_service.embed_query.assert_not_called()
        for call in mock_opensearch_client.query.call_args_list:
            assert knn_vector_from_search_body(call.args[1]) == embedding

    def test_run_experiment_normalizes_string_mode_keys(
        self,
        retriever: Retriever,
        mock_opensearch_client: Mock,
    ) -> None:
        request = RetrieveExperimentRequest(
            query="fever",
            modes=[RetrievalMode.BM25],
        )
        # RWSBaseModel stores enum values as strings after validation.
        request = request.model_copy(update={"modes": ["bm25"]})

        response = retriever.run_experiment(request)

        assert RetrievalMode.BM25 in response.results

    def test_run_experiment_skips_preprocess_when_disabled(
        self,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
    ) -> None:
        retriever = Retriever(
            embed_service=mock_embed_service,
            client=mock_opensearch_client,
            preprocess=False,
        )
        request = RetrieveExperimentRequest(
            query="I am tired",
            modes=[RetrievalMode.BM25],
        )

        response = retriever.run_experiment(request)

        body = mock_opensearch_client.query.call_args.args[1]
        assert body["query"]["match"]["keyword_text"]["query"] == "I am tired"
        assert response.query == "I am tired"

    def test_run_experiment_empty_modes_logs_warning(
        self,
        retriever: Retriever,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        request = RetrieveExperimentRequest(query="fever", modes=[])

        response = retriever.run_experiment(request)

        assert response.results == {}
        assert response.modes_run == []
        assert "empty modes list" in caplog.text
