"""Retrieval request/response schemas for step-by-step RAG search experiments."""

from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from src.schemas.base import ORSBaseModel, RWSBaseModel
from src.settings import settings

MatchOperator = Literal["or", "and"]


def _default_source_fields() -> list[str]:
    return list(settings.RETRIEVE_SOURCE_FIELDS)


class RetrievalMode(str, Enum):
    BM25 = "bm25"
    KNN = "knn"
    HYBRID = "hybrid"


class RetrieveBaseRequest(RWSBaseModel):
    """Shared fields for all retrieval test requests."""

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=20, ge=1, le=100)
    index_name: str = Field(default_factory=lambda: settings.RETRIEVE_INDEX_ALIAS)
    source_fields: list[str] = Field(default_factory=_default_source_fields)
    explain: bool = False


class Bm25RetrieveRequest(RetrieveBaseRequest):
    """BM25 lexical search on ``keyword_text`` (or another analyzed text field)."""

    field: str = "keyword_text"
    operator: MatchOperator = "or"
    minimum_should_match: int | str | None = None

    def to_search_body(self) -> dict[str, Any]:
        match_query: dict[str, Any] = {"query": self.query, "operator": self.operator}
        if self.minimum_should_match is not None:
            match_query["minimum_should_match"] = self.minimum_should_match

        body: dict[str, Any] = {
            "size": self.top_k,
            "_source": self.source_fields,
            "query": {"match": {self.field: match_query}},
        }
        if self.explain:
            body["explain"] = True
        return body


class VectorRetrieveRequest(RetrieveBaseRequest):
    """k-NN vector search on ``embedding`` (384-dim cosine)."""

    field: str = "embedding"
    knn_k: int | None = None
    embedding: list[float] | None = Field(
        default=None,
        description="Optional fixed vector for reproducible experiments. "
        "If omitted, the retriever embeds ``query``.",
    )

    @model_validator(mode="after")
    def validate_embedding_dimension(self) -> "VectorRetrieveRequest":
        if self.embedding is not None and len(self.embedding) != 384:
            msg = f"embedding must be 384-dimensional, got {len(self.embedding)}"
            raise ValueError(msg)
        return self

    def resolved_k(self) -> int:
        return self.knn_k or self.top_k

    def to_search_body(self, embedding: list[float]) -> dict[str, Any]:
        if len(embedding) != 384:
            msg = f"embedding must be 384-dimensional, got {len(embedding)}"
            raise ValueError(msg)

        body: dict[str, Any] = {
            "size": self.top_k,
            "_source": self.source_fields,
            "query": {
                "knn": {
                    self.field: {
                        "vector": embedding,
                        "k": self.resolved_k(),
                    }
                }
            },
        }
        if self.explain:
            body["explain"] = True
        return body


class HybridRetrieveRequest(RetrieveBaseRequest):
    """Hybrid BM25 + k-NN fused with RRF via a search pipeline."""

    search_pipeline: str = Field(
        default_factory=lambda: settings.CURRENT_SEARCH_PIPELINE
    )
    bm25_field: str = "keyword_text"
    vector_field: str = "embedding"
    bm25_operator: MatchOperator = "or"
    knn_k: int = Field(
        default=20,
        ge=1,
        le=100,
        description="The number of nearest neighbors to retrieve for the vector search.",
    )
    embedding: list[float] | None = Field(
        default=None,
        description="Optional fixed vector for reproducible experiments.",
    )

    @model_validator(mode="after")
    def validate_embedding_dimension(self) -> "HybridRetrieveRequest":
        if self.embedding is not None and len(self.embedding) != 384:
            msg = f"embedding must be 384-dimensional, got {len(self.embedding)}"
            raise ValueError(msg)
        return self

    def resolved_k(self) -> int:
        return self.knn_k or self.top_k

    def to_search_body(self, embedding: list[float]) -> dict[str, Any]:
        if len(embedding) != 384:
            msg = f"embedding must be 384-dimensional, got {len(embedding)}"
            raise ValueError(msg)

        body: dict[str, Any] = {
            "size": self.top_k,
            "_source": self.source_fields,
            "query": {
                "hybrid": {
                    "queries": [
                        {
                            "match": {
                                self.bm25_field: {
                                    "query": self.query,
                                    "operator": self.bm25_operator,
                                }
                            }
                        },
                        {
                            "knn": {
                                self.vector_field: {
                                    "vector": embedding,
                                    "k": self.resolved_k(),
                                }
                            }
                        },
                    ]
                }
            },
        }
        if self.explain:
            body["explain"] = True
        return body


class RetrieveExperimentRequest(RWSBaseModel):
    """Run the same query through multiple retrieval modes for comparison."""

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=20, ge=1, le=100)
    index_name: str = Field(default_factory=lambda: settings.RETRIEVE_INDEX_ALIAS)
    search_pipeline: str = Field(
        default_factory=lambda: settings.CURRENT_SEARCH_PIPELINE
    )
    modes: list[RetrievalMode] = Field(
        default_factory=lambda: [
            RetrievalMode.BM25,
            RetrievalMode.KNN,
            RetrievalMode.HYBRID,
        ]
    )
    source_fields: list[str] = Field(default_factory=_default_source_fields)
    include_opensearch_body: bool = Field(
        default=False,
        description="Include raw OpenSearch request bodies in each result (debug).",
    )
    explain: bool = False

    def bm25_request(self) -> Bm25RetrieveRequest:
        return Bm25RetrieveRequest(
            query=self.query,
            top_k=self.top_k,
            index_name=self.index_name,
            source_fields=self.source_fields,
            explain=self.explain,
        )

    def vector_request(self) -> VectorRetrieveRequest:
        return VectorRetrieveRequest(
            query=self.query,
            top_k=self.top_k,
            index_name=self.index_name,
            source_fields=self.source_fields,
            explain=self.explain,
        )

    def hybrid_request(self) -> HybridRetrieveRequest:
        return HybridRetrieveRequest(
            query=self.query,
            top_k=self.top_k,
            index_name=self.index_name,
            source_fields=self.source_fields,
            search_pipeline=self.search_pipeline,
            explain=self.explain,
        )


class RetrieveHit(ORSBaseModel):
    """Normalized document hit for retrieval and reranking."""

    rank: int
    score: float | None
    doc_id: str | None = None
    disease: str | None = None
    symptoms: list[str] | None = None
    antecedents: list[str] | None = None
    severity: int | None = None
    description: str | None = None
    source: str | None = None


class RetrieveResult(ORSBaseModel):
    """Slim retrieval output for production paths (rerank, generate)."""

    hits: list[RetrieveHit]
    took_ms: int | None = None


class ExperimentModeResult(ORSBaseModel):
    """Single-mode result with experiment and optional debug metadata."""

    mode: RetrievalMode
    hits: list[RetrieveHit]
    took_ms: int
    total_hits: int
    search_pipeline: str | None = None
    opensearch_body: dict[str, Any] | None = None


class ExperimentCompareResponse(ORSBaseModel):
    """Side-by-side results from ``RetrieveExperimentRequest``."""

    query: str
    top_k: int
    index_name: str
    results: dict[str, ExperimentModeResult]

    @property
    def modes_run(self) -> list[str]:
        return list(self.results.keys())
