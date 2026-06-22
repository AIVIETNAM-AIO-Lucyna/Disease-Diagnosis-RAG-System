"""Unit tests for reranking helpers and Retriever.rerank()."""

from unittest.mock import Mock

import pytest

from src.services.rag.exceptions import RerankerNotConfigured
from src.services.rag.retrieve import Retriever
from src.services.rag.schemas import RetrieveHit, RetrieveResult


def _sample_hit(
    *,
    rank: int = 1,
    score: float = 1.0,
    doc_id: str = "G70.0",
    disease: str = "Myasthenia gravis",
    symptoms: list[str] | None = None,
    antecedents: list[str] | None = None,
    severity: int = 1,
    description: str = "Example description",
    source: str = "ddxplus",
) -> RetrieveHit:
    return RetrieveHit(
        rank=rank,
        score=score,
        doc_id=doc_id,
        disease=disease,
        symptoms=symptoms if symptoms is not None else ["fatigue", "muscle weakness"],
        antecedents=antecedents if antecedents is not None else [],
        severity=severity,
        description=description,
        source=source,
    )


class TestRetrieveHitPassageText:
    def test_builds_symptom_first_template(self) -> None:
        hit = _sample_hit()

        assert hit.passage_text == (
            "Disease: Myasthenia gravis. "
            "Symptoms: fatigue, muscle weakness. "
            "Example description"
        )

    def test_omits_symptoms_when_empty(self) -> None:
        hit = _sample_hit(symptoms=[])

        assert hit.passage_text == "Disease: Myasthenia gravis. Example description"


class TestRetrieverRerank:
    def test_rerank_reorders_hits_and_updates_scores(
        self,
        retriever_with_rerank: Retriever,
        mock_rerank_service: Mock,
    ) -> None:
        result = RetrieveResult(
            hits=[
                _sample_hit(rank=1, score=1.42, doc_id="A"),
                _sample_hit(rank=2, score=0.8, doc_id="B"),
            ],
            took_ms=12,
        )
        mock_rerank_service.rerank.return_value = [(1, 0.95), (0, 0.5)]

        reranked = retriever_with_rerank.rerank("fever", result, top_k=2)

        mock_rerank_service.rerank.assert_called_once()
        query, passages = mock_rerank_service.rerank.call_args.args
        assert query == "fever"
        assert len(passages) == 2
        assert passages[0] == result.hits[0].passage_text
        assert passages[1] == result.hits[1].passage_text
        assert mock_rerank_service.rerank.call_args.kwargs["top_k"] == 2
        assert reranked.took_ms == 12
        assert len(reranked.hits) == 2
        assert reranked.hits[0].doc_id == "B"
        assert reranked.hits[0].rank == 1
        assert reranked.hits[0].score == 0.95
        assert reranked.hits[1].doc_id == "A"
        assert reranked.hits[1].rank == 2
        assert reranked.hits[1].score == 0.5

    def test_rerank_preprocesses_query_by_default(
        self,
        retriever_with_rerank: Retriever,
        mock_rerank_service: Mock,
    ) -> None:
        result = RetrieveResult(hits=[_sample_hit()], took_ms=12)

        retriever_with_rerank.rerank("I am tired", result, top_k=1)

        query = mock_rerank_service.rerank.call_args.args[0]
        assert query == "i am fatigue"

    def test_rerank_skips_preprocess_when_disabled(
        self,
        mock_embed_service: Mock,
        mock_opensearch_client: Mock,
        mock_rerank_service: Mock,
    ) -> None:
        retriever = Retriever(
            client=mock_opensearch_client,
            embed_service=mock_embed_service,
            rerank_service=mock_rerank_service,
            preprocess=False,
        )
        result = RetrieveResult(hits=[_sample_hit()], took_ms=12)

        retriever.rerank("I am tired", result, top_k=1)

        query = mock_rerank_service.rerank.call_args.args[0]
        assert query == "I am tired"

    def test_rerank_returns_empty_result_unchanged(
        self,
        retriever_with_rerank: Retriever,
        mock_rerank_service: Mock,
    ) -> None:
        result = RetrieveResult(hits=[], took_ms=5)

        reranked = retriever_with_rerank.rerank("fever", result, top_k=5)

        assert reranked == result
        mock_rerank_service.rerank.assert_not_called()

    def test_rerank_raises_when_service_not_configured(
        self,
        retriever_without_rerank: Retriever,
    ) -> None:
        result = RetrieveResult(hits=[_sample_hit()], took_ms=12)

        with pytest.raises(RerankerNotConfigured, match="Reranker is not configured"):
            retriever_without_rerank.rerank("fever", result, top_k=5)
