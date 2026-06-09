"""Retrieval: BM25, k-NN, and hybrid+RRF search."""

from typing import Any

from src.db.vector_db.opensearch import OpenSearchClient, get_opensearch_client
from src.schemas import SearchResponse
from src.services.ai_inference.bge.service import BGEInferenceService
from src.services.rag.preprocess import preprocess_query
from src.services.rag.schemas import (
    Bm25RetrieveRequest,
    ExperimentCompareResponse,
    ExperimentModeResult,
    HybridRetrieveRequest,
    RetrievalMode,
    RetrieveExperimentRequest,
    RetrieveHit,
    RetrieveResult,
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

    def search_bm25(self, request: Bm25RetrieveRequest) -> RetrieveResult:
        request = self._maybe_preprocess_request(request)
        body = request.to_search_body()
        response = self._client.query(request.index_name, body)
        return self._to_retrieve_result(response)

    def search_vector(self, request: VectorRetrieveRequest) -> RetrieveResult:
        request = self._maybe_preprocess_request(request)
        embedding = request.embedding or self._embed_service.embed_query(request.query)
        body = request.to_search_body(embedding)
        response = self._client.query(request.index_name, body)
        return self._to_retrieve_result(response)

    def search_hybrid(self, request: HybridRetrieveRequest) -> RetrieveResult:
        request = self._maybe_preprocess_request(request)
        embedding = request.embedding or self._embed_service.embed_query(request.query)
        body = request.to_search_body(embedding)
        response = self._client.query(
            request.index_name,
            body,
            search_pipeline=request.search_pipeline,
        )
        return self._to_retrieve_result(response)

    def run_experiment(
        self, request: RetrieveExperimentRequest
    ) -> ExperimentCompareResponse:
        """Compare BM25, k-NN, and/or hybrid on the same query."""
        if self._preprocess:
            request = request.model_copy(
                update={"query": preprocess_query(request.query)}
            )

        results: dict[str, ExperimentModeResult] = {}

        for mode in request.modes:
            if mode is RetrievalMode.BM25:
                bm25 = request.bm25_request()
                body = bm25.to_search_body()
                response = self._client.query(request.index_name, body)
                mode_result = self._to_experiment_mode_result(
                    mode=mode,
                    response=response,
                    opensearch_body=body if request.include_opensearch_body else None,
                )

            elif mode is RetrievalMode.KNN:
                vector = request.vector_request()
                embedding = self._embed_service.embed_query(vector.query)
                body = vector.to_search_body(embedding)
                response = self._client.query(request.index_name, body)
                mode_result = self._to_experiment_mode_result(
                    mode=mode,
                    response=response,
                    opensearch_body=body if request.include_opensearch_body else None,
                )

            elif mode is RetrievalMode.HYBRID:
                hybrid = request.hybrid_request()
                embedding = self._embed_service.embed_query(hybrid.query)
                body = hybrid.to_search_body(embedding)
                response = self._client.query(
                    request.index_name,
                    body,
                    search_pipeline=hybrid.search_pipeline,
                )
                mode_result = self._to_experiment_mode_result(
                    mode=mode,
                    response=response,
                    search_pipeline=hybrid.search_pipeline,
                    opensearch_body=body if request.include_opensearch_body else None,
                )

            else:
                continue

            results[mode.value] = mode_result

        return ExperimentCompareResponse(
            query=request.query,
            top_k=request.top_k,
            index_name=request.index_name,
            results=results,
        )

    def retrieve(
        self, query: str, index_name: str | None = None
    ) -> RetrieveResult:
        index_name = index_name or settings.RETRIEVE_INDEX_ALIAS
        return self.search_hybrid(
            HybridRetrieveRequest(query=query, index_name=index_name)
        )

    def _maybe_preprocess_request(self, request: Any) -> Any:
        if not self._preprocess:
            return request
        return request.model_copy(update={"query": preprocess_query(request.query)})

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
                    severity=source.get("severity"),
                    description=source.get("description"),
                    precautions=source.get("precautions"),
                )
            )
        return hits

    @staticmethod
    def _total_hits(response: SearchResponse) -> int:
        total = response.hits.total
        return total.value if hasattr(total, "value") else int(total)

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
