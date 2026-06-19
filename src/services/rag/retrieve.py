"""Retrieval: BM25, k-NN, and hybrid+RRF search."""

from typing import Any

from src.db.vector_db.opensearch import OpenSearchClient, get_opensearch_client
from src.logging import get_logger
from src.schemas import SearchResponse
from src.schemas.opensearch_responses import TotalHits
from src.services.ai_inference.bge.service import BGEInferenceService
from src.services.rag.preprocess import preprocess_query
from src.services.rag.schemas import (
    Bm25RetrieveRequest,
    ExperimentCompareResponse,
    ExperimentModeResult,
    HybridRetrieveRequest,
    PreprocessableRequest,
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
        embed_service: BGEInferenceService,
        client: OpenSearchClient | None = None,
        *,
        preprocess: bool = True,
    ) -> None:
        self._client = client or get_opensearch_client()
        self._embed_service = embed_service
        self._preprocess = preprocess
        self._logger = get_logger(__name__)

    def search_bm25(self, request: Bm25RetrieveRequest) -> RetrieveResult:
        request = self._maybe_preprocess_request(request)
        return self._execute_bm25(request).result

    def search_vector(self, request: VectorRetrieveRequest) -> RetrieveResult:
        request = self._maybe_preprocess_request(request)
        return self._execute_vector(request).result

    def search_hybrid(self, request: HybridRetrieveRequest) -> RetrieveResult:
        request = self._maybe_preprocess_request(request)
        return self._execute_hybrid(request).result

    def run_experiment(
        self, request: RetrieveExperimentRequest
    ) -> ExperimentCompareResponse:
        """Compare BM25, k-NN, and/or hybrid on the same query."""
        if self._preprocess:
            request = request.model_copy(
                update={"query": preprocess_query(request.query)}
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

    def _maybe_preprocess_request(
        self, request: PreprocessableRequest
    ) -> PreprocessableRequest:
        if not self._preprocess:
            return request
        return request.model_copy(update={"query": preprocess_query(request.query)})

    @staticmethod
    def _normalize_mode(mode: RetrievalMode | str) -> RetrievalMode:
        return mode if isinstance(mode, RetrievalMode) else RetrievalMode(mode)

    @staticmethod
    def _build_hits(response: SearchResponse) -> list[RetrieveHit]:
        hits: list[RetrieveHit] = []
        for rank, hit in enumerate(response.hits.hits, start=1):
            source = hit.source or {}
            hits.append(
                RetrieveHit(
                    rank=rank,
                    score=hit.score,
                    doc_id=source.get("doc_id"),
                    disease=source.get("disease"),
                    symptoms=source.get("symptoms"),
                    antecedents=source.get("antecedents"),
                    severity=source.get("severity"),
                    description=source.get("description"),
                    source=source.get("source"),
                )
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
