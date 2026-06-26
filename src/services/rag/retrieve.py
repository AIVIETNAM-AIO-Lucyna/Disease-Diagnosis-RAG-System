"""Retrieval: BM25, k-NN, and hybrid+RRF search."""

from typing import Any, Optional

from pydantic import ValidationError

from src.db.vector_db.opensearch import OpenSearchClient
from src.logging import get_logger
from src.schemas import SearchResponse
from src.schemas.opensearch_responses import TotalHits
from src.services.inference.embeddings.service import TextEmbeddingService
from src.services.inference.reranker.service import RerankerService
from src.services.rag.exceptions import RerankerNotConfigured
from src.services.rag.preprocess import PreprocessPipeline
from src.services.rag.schemas import (
    Bm25RetrieveRequest,
    ExperimentCompareResponse,
    ExperimentModeResult,
    HybridRetrieveRequest,
    RetrievalMode,
    RetrieveExperimentRequest,
    RetrieveHit,
    RetrieveResult,
    SearchExecution,
    VectorRetrieveRequest,
)
from src.settings import settings


class Retriever:
    """Step-by-step retrieval API for team experiments."""

    def __init__(
        self,
        client: OpenSearchClient,
        embed_service: TextEmbeddingService,
        preprocess: PreprocessPipeline,
        rerank_service: Optional[RerankerService] = None,
    ) -> None:
        self._client = client
        self._embed_service = embed_service
        self._preprocess = preprocess
        self._rerank_service = rerank_service
        self._logger = get_logger(__name__)

    def search_bm25(self, request: Bm25RetrieveRequest) -> RetrieveResult:
        request = request.model_copy(
            update={"query": self._preprocess.preprocess_query(request.query)}
        )
        return self._execute_bm25(request).result

    def search_vector(self, request: VectorRetrieveRequest) -> RetrieveResult:
        request = request.model_copy(
            update={"query": self._preprocess.preprocess_query(request.query)}
        )
        return self._execute_vector(request).result

    def search_hybrid(self, request: HybridRetrieveRequest) -> RetrieveResult:
        request = request.model_copy(
            update={"query": self._preprocess.preprocess_query(request.query)}
        )
        return self._execute_hybrid(request).result

    def run_experiment(
        self, request: RetrieveExperimentRequest
    ) -> ExperimentCompareResponse:
        """Compare BM25, k-NN, and/or hybrid on the same query."""
        request = request.model_copy(
            update={"query": self._preprocess.preprocess_query(request.query)}
        )

        if not request.modes:
            self._logger.warning("run_experiment called with an empty modes list")

        request = self._ensure_experiment_embedding(request)
        results: dict[RetrievalMode, ExperimentModeResult] = {}

        for mode in request.modes:
            if mode == RetrievalMode.BM25:
                execution = self._execute_bm25(request.bm25_request())
            elif mode == RetrievalMode.KNN:
                execution = self._execute_vector(request.vector_request())
            elif mode == RetrievalMode.HYBRID:
                execution = self._execute_hybrid(request.hybrid_request())
            else:
                continue

            mode_key = self._normalize_mode(mode)
            results[mode_key] = self._to_experiment_mode_result(
                mode=mode_key,
                response=execution.response,
                search_pipeline=execution.search_pipeline,
                opensearch_body=(
                    execution.body if request.include_opensearch_body else None
                ),
            )

        return ExperimentCompareResponse(
            query=request.query,
            top_k=request.top_k,
            index_name=request.index_name,
            results=results,
        )

    def retrieve(self, query: str, index_name: str | None = None) -> RetrieveResult:
        index_name = index_name or settings.RETRIEVE_INDEX_ALIAS
        return self.search_hybrid(
            HybridRetrieveRequest(query=query, index_name=index_name)
        )

    def rerank(
        self,
        query: str,
        result: RetrieveResult,
        top_k: int,
    ) -> RetrieveResult:
        """Rerank retrieval hits with the cross-encoder and return top_k hits."""
        if self._rerank_service is None:
            raise RerankerNotConfigured()

        if not result.hits:
            return result

        query = self._preprocess.preprocess_query(query)

        passages = [hit.passage_text for hit in result.hits]
        ranked = self._rerank_service.rerank(query, passages, top_k=top_k)

        reranked_hits: list[RetrieveHit] = []
        for new_rank, (original_index, score) in enumerate(ranked, start=1):
            hit = result.hits[original_index].model_copy(
                update={"rank": new_rank, "score": score}
            )
            reranked_hits.append(hit)

        return result.model_copy(update={"hits": reranked_hits})

    def _execute_bm25(self, request: Bm25RetrieveRequest) -> SearchExecution:
        body = request.to_search_body()
        response = self._client.query(request.index_name, body)
        return SearchExecution(
            result=self._to_retrieve_result(response),
            response=response,
            body=body,
        )

    def _execute_vector(self, request: VectorRetrieveRequest) -> SearchExecution:
        request = self._ensure_request_embedding(request)
        body = request.to_search_body()
        response = self._client.query(request.index_name, body)
        return SearchExecution(
            result=self._to_retrieve_result(response),
            response=response,
            body=body,
        )

    def _execute_hybrid(self, request: HybridRetrieveRequest) -> SearchExecution:
        request = self._ensure_request_embedding(request)
        body = request.to_search_body()
        response = self._client.query(
            request.index_name,
            body,
            search_pipeline=request.search_pipeline,
        )
        return SearchExecution(
            result=self._to_retrieve_result(response),
            response=response,
            body=body,
            search_pipeline=request.search_pipeline,
        )

    def _ensure_experiment_embedding(
        self, request: RetrieveExperimentRequest
    ) -> RetrieveExperimentRequest:
        """Set ``request.embedding`` once when vector/hybrid modes need a query vector."""
        if request.embedding is not None:
            return request

        needs_embedding = any(
            mode == RetrievalMode.KNN or mode == RetrievalMode.HYBRID
            for mode in request.modes
        )
        if not needs_embedding:
            return request

        return request.model_copy(
            update={"embedding": self._embed_service.embed_query(request.query)}
        )

    def _ensure_request_embedding(
        self, request: VectorRetrieveRequest | HybridRetrieveRequest
    ) -> VectorRetrieveRequest | HybridRetrieveRequest:
        if request.embedding is not None:
            return request
        return request.model_copy(
            update={"embedding": self._embed_service.embed_query(request.query)}
        )

    @staticmethod
    def _normalize_mode(mode: RetrievalMode | str) -> RetrievalMode:
        return mode if isinstance(mode, RetrievalMode) else RetrievalMode(mode)

    @staticmethod
    def _build_hits(response: SearchResponse) -> list[RetrieveHit]:
        logger = get_logger(__name__)
        hits: list[RetrieveHit] = []
        rank = 0
        for hit in response.hits.hits:
            source = hit.source
            if source is None:
                continue

            required_fields = ("doc_id", "disease", "severity", "source")
            if any(source.get(field) in (None, "") for field in required_fields):
                continue

            rank += 1
            try:
                hits.append(
                    RetrieveHit(
                        rank=rank,
                        score=hit.score,
                        doc_id=source["doc_id"],
                        disease=source["disease"],
                        symptoms=source.get("symptoms") or [],
                        antecedents=source.get("antecedents") or [],
                        severity=source["severity"],
                        description=source.get("description") or "",
                        source=source["source"],
                    )
                )
            except ValidationError as exc:
                rank -= 1
                logger.warning(
                    "skipping_invalid_hit",
                    error=str(exc),
                    doc_id=source.get("doc_id"),
                )
        return hits

    @staticmethod
    def _total_hits(response: SearchResponse) -> int:
        total = response.hits.total
        if isinstance(total, TotalHits):
            return total.value
        return int(total)

    @classmethod
    def _to_retrieve_result(cls, response: SearchResponse) -> RetrieveResult:
        return RetrieveResult(hits=cls._build_hits(response), took_ms=response.took)

    @classmethod
    def _to_experiment_mode_result(
        cls,
        *,
        mode: RetrievalMode,
        response: SearchResponse,
        search_pipeline: str | None = None,
        opensearch_body: dict[str, Any] | None = None,
    ) -> ExperimentModeResult:
        return ExperimentModeResult(
            mode=mode,
            hits=cls._build_hits(response),
            took_ms=response.took,
            total_hits=cls._total_hits(response),
            search_pipeline=search_pipeline,
            opensearch_body=opensearch_body,
        )
