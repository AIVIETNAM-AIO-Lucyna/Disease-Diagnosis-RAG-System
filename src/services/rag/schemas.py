"""Retrieval request/response schemas for step-by-step RAG search experiments."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, TypeVar

from pydantic import Field, computed_field, model_validator

from src.schemas import SearchResponse
from src.schemas.base import ORSBaseModel, RWSBaseModel
from src.services.rag.preprocess import normalize_symptoms
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
    top_k: int = Field(default=settings.RETRIEVE_TOP_K, ge=1, le=100)
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
    """k-NN vector search on ``embedding`` (settings.EMBEDDING_DIM-dim cosine)."""

    field: str = "embedding"
    knn_k: int | None = None
    embedding: list[float] | None = Field(
        default=None,
        description="Optional fixed vector for reproducible experiments. "
        "If omitted, the retriever embeds ``query``.",
    )

    @model_validator(mode="after")
    def validate_embedding_dimension(self) -> "VectorRetrieveRequest":
        if self.embedding is not None and len(self.embedding) != settings.EMBEDDING_DIM:
            msg = f"embedding must be settings.EMBEDDING_DIM-dimensional, got {len(self.embedding)}"
            raise ValueError(msg)
        return self

    def resolved_k(self) -> int:
        return self.knn_k or self.top_k

    def to_search_body(self) -> dict[str, Any]:
        if self.embedding is None:
            msg = "embedding must be set before building the search body"
            raise ValueError(msg)

        body: dict[str, Any] = {
            "size": self.top_k,
            "_source": self.source_fields,
            "query": {
                "knn": {
                    self.field: {
                        "vector": self.embedding,
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
        if self.embedding is not None and len(self.embedding) != settings.EMBEDDING_DIM:
            msg = f"embedding must be settings.EMBEDDING_DIM-dimensional, got {len(self.embedding)}"
            raise ValueError(msg)
        return self

    def resolved_k(self) -> int:
        return self.knn_k or self.top_k

    def to_search_body(self) -> dict[str, Any]:
        if self.embedding is None:
            msg = "embedding must be set before building the search body"
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
                                    "vector": self.embedding,
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


PreprocessableRequest = TypeVar(
    "PreprocessableRequest",
    Bm25RetrieveRequest,
    VectorRetrieveRequest,
    HybridRetrieveRequest,
)


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
    embedding: list[float] | None = Field(
        default=None,
        description="Optional fixed vector shared across vector/hybrid modes.",
    )
    include_opensearch_body: bool = Field(
        default=False,
        description="Include raw OpenSearch request bodies in each result (debug).",
    )
    explain: bool = False

    @model_validator(mode="after")
    def validate_embedding_dimension(self) -> "RetrieveExperimentRequest":
        if self.embedding is not None and len(self.embedding) != settings.EMBEDDING_DIM:
            msg = (
                f"embedding must be {settings.EMBEDDING_DIM}-dimensional, "
                f"got {len(self.embedding)}"
            )
            raise ValueError(msg)
        return self

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
            embedding=self.embedding,
        )

    def hybrid_request(self) -> HybridRetrieveRequest:
        return HybridRetrieveRequest(
            query=self.query,
            top_k=self.top_k,
            index_name=self.index_name,
            source_fields=self.source_fields,
            search_pipeline=self.search_pipeline,
            explain=self.explain,
            embedding=self.embedding,
        )


class RetrieveHit(ORSBaseModel):
    """Normalized document hit for retrieval and reranking."""

    rank: int
    score: float | None = None
    doc_id: str = Field(..., min_length=1)
    disease: str = Field(..., min_length=1)
    symptoms: list[str] = Field(default_factory=list)
    antecedents: list[str] = Field(default_factory=list)
    severity: int = Field(..., ge=1, le=5)
    description: str = ""
    source: str = Field(..., min_length=1)

    @property
    def passage_text(self) -> str:
        """Build symptom-first passage text for cross-encoder reranking."""
        parts = [f"Disease: {self.disease}."]
        if self.symptoms:
            symptom_str = ", ".join(self.symptoms)
            parts.append(f"Symptoms: {symptom_str}.")
        if self.description:
            parts.append(self.description)
        return " ".join(parts)


class RetrieveResult(ORSBaseModel):
    """Slim retrieval output for production paths (rerank, generate)."""

    hits: list[RetrieveHit]
    took_ms: int | None = None


@dataclass(frozen=True)
class SearchExecution:
    """Result of a single OpenSearch retrieval call before response mapping."""

    result: RetrieveResult
    response: SearchResponse
    body: dict[str, Any]
    search_pipeline: str | None = None


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
    results: dict[RetrievalMode, ExperimentModeResult]

    @property
    def modes_run(self) -> list[str]:
        return [mode.value for mode in self.results]


class DiseaseDocument(RWSBaseModel):
    """Disease document for ingestion and OpenSearch bulk upsert.

    Use without ``embedding`` when loading source records; ``Ingestion`` normalizes
    symptoms/antecedents, embeds ``embed_text``, sets ``embedding``, then bulk-indexes.
    ``keyword_text`` is always derived for BM25; it is included in bulk payloads via
    ``to_bulk_action()``.
    """

    doc_id: str = Field(..., min_length=1)
    disease: str = Field(..., min_length=1)
    symptoms: list[str]
    severity: int = Field(..., ge=1, le=5)
    source: str = Field(..., min_length=1)
    antecedents: list[str] = Field(default_factory=list)
    description: str = ""
    embedding: list[float] | None = None

    @property
    def embed_text(self) -> str:
        symptom_str = ", ".join(normalize_symptoms(self.symptoms))
        return f"Disease: {self.disease}. Symptoms: {symptom_str}. {self.description}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def keyword_text(self) -> str:
        parts = [
            self.disease.strip(),
            *normalize_symptoms(self.symptoms),
            *normalize_symptoms(self.antecedents),
        ]
        return " ".join(part for part in parts if part)

    @model_validator(mode="after")
    def validate_embedding_dimension(self) -> "DiseaseDocument":
        if self.embedding is not None and len(self.embedding) != settings.EMBEDDING_DIM:
            msg = (
                f"embedding must be {settings.EMBEDDING_DIM}-dimensional, "
                f"got {len(self.embedding)}"
            )
            raise ValueError(msg)
        return self

    def to_bulk_action(self, index_name: str) -> dict[str, Any]:
        if self.embedding is None:
            msg = "embedding must be set before building a bulk action"
            raise ValueError(msg)
        return {
            "_index": index_name,
            "_id": self.doc_id,
            **self.to_dict(),
        }


class BulkIngestRequest(RWSBaseModel):
    """Bulk upsert request for indexed disease documents."""

    index_name: str = Field(default_factory=lambda: settings.RETRIEVE_INDEX_ALIAS)

    documents: list[DiseaseDocument] = Field(
        ...,
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_documents_have_embeddings(self) -> "BulkIngestRequest":
        missing = [doc.doc_id for doc in self.documents if doc.embedding is None]
        if missing:
            msg = f"documents missing embedding: {missing[:3]}"
            raise ValueError(msg)
        return self

    def to_bulk_actions(self) -> list[dict[str, Any]]:
        return [doc.to_bulk_action(self.index_name) for doc in self.documents]
