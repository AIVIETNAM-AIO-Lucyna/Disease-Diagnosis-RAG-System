"""Unit tests for ``src.services.rag.pipeline.RAGService``."""

from unittest.mock import Mock, patch

from src.services.rag.pipeline import RAGService
from src.services.rag.schemas import RetrieveHit, RetrieveResult
from src.settings import settings


class TestRAGService:
    @patch("src.services.rag.pipeline.get_opensearch_client")
    @patch("src.services.rag.pipeline.TextEmbeddingService")
    @patch("src.services.rag.pipeline.RerankerService")
    def test_query_runs_retrieve_then_rerank(
        self,
        mock_reranker_cls: Mock,
        mock_bge_cls: Mock,
        mock_get_client: Mock,
    ) -> None:
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_embed_service = Mock()
        mock_bge_cls.return_value = mock_embed_service
        mock_rerank_service = Mock()
        mock_reranker_cls.return_value = mock_rerank_service

        retrieve_result = RetrieveResult(
            hits=[
                RetrieveHit(
                    rank=1,
                    score=1.42,
                    doc_id="G70.0",
                    disease="Myasthenia gravis",
                    symptoms=["fatigue"],
                    severity=1,
                    source="ddxplus",
                )
            ],
            took_ms=12,
        )
        rerank_result = RetrieveResult(
            hits=[
                RetrieveHit(
                    rank=1,
                    score=0.99,
                    doc_id="G70.0",
                    disease="Myasthenia gravis",
                    symptoms=["fatigue"],
                    severity=1,
                    source="ddxplus",
                )
            ],
            took_ms=12,
        )

        with patch("src.services.rag.pipeline.Retriever") as mock_retriever_cls:
            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = retrieve_result
            mock_retriever.rerank.return_value = rerank_result
            mock_retriever_cls.return_value = mock_retriever

            service = RAGService()
            result = service.query("fever cough")

        mock_retriever.retrieve.assert_called_once_with("fever cough", index_name=None)
        mock_retriever.rerank.assert_called_once_with(
            "fever cough",
            retrieve_result,
            top_k=settings.RERANK_TOP_K,
        )
        assert result == rerank_result

    @patch("src.services.rag.pipeline.get_opensearch_client")
    def test_query_uses_injected_retriever(self, mock_get_client: Mock) -> None:
        mock_retriever = Mock()
        expected = RetrieveResult(hits=[], took_ms=0)
        mock_retriever.retrieve.return_value = expected
        mock_retriever.rerank.return_value = expected

        service = RAGService(retriever=mock_retriever)
        result = service.query("fever", index_name="custom-index")

        mock_retriever.retrieve.assert_called_once_with(
            "fever", index_name="custom-index"
        )
        mock_retriever.rerank.assert_called_once_with(
            "fever",
            expected,
            top_k=settings.RERANK_TOP_K,
        )
        assert result == expected
