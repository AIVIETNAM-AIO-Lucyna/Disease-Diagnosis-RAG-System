from pathlib import Path

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_project_path(path: str) -> Path:
    """Resolve ``path`` against ``PROJECT_ROOT`` when it is relative."""
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    return PROJECT_ROOT / resolved


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
    )

    # OpenSearch
    OPENSEARCH_HOST: str = Field(..., description="The host of the OpenSearch instance")
    OPENSEARCH_PORT: int = Field(..., description="The port of the OpenSearch instance")
    OPENSEARCH_USERNAME: str = Field(
        ..., description="The username of the OpenSearch instance"
    )
    OPENSEARCH_PASSWORD: str = Field(
        ..., description="The password of the OpenSearch instance"
    )

    PATH_TO_MODELS: str = Field(
        default="models",
        description="Path to the models directory, relative to the project root",
    )
    # Vector search
    EMBEDDING_MODEL_REPO_ID: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="The repository ID of the embedding model",
    )
    EMBEDDING_MODEL: str = Field(
        default="bge-small-en-v1.5",  # english model, version 1.5
        description="The name of the embedding model to use for vector search",
    )
    EMBEDDING_DIM: int = Field(
        default=384,
        description="The dimension of the embedding vector",
    )
    # Reranker
    RERANKER_MODEL_REPO_ID: str = Field(
        default="BAAI/bge-reranker-base",
        description="The repository ID of the cross-encoder reranker model",
    )
    RERANKER_MODEL: str = Field(
        default="bge-reranker-base",
        description="The local directory name for the reranker model",
    )
    RERANK_TOP_K: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of hits to keep after cross-encoder reranking",
    )
    # PATH
    PATH_TO_INDICES: str = Field(
        default="indices",
        description="Path to the indices directory, relative to the project root",
    )
    CURRENT_INDEX_MAPPING: str = Field(
        default="diseases/ddxplus_mapping.json",
        description="The path to the current index mapping",
    )
    CURRENT_SEARCH_PIPELINE: str = Field(
        default="hybrid-rrf",
        description="The name of the current search pipeline",
    )

    # Retrieval
    RETRIEVE_TOP_K: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of hits to keep after retrieval",
    )
    RETRIEVE_INDEX_ALIAS: str = Field(
        default="diseases",
        description="OpenSearch index alias used for retrieval queries",
    )
    RETRIEVE_SOURCE_FIELDS: list[str] = Field(
        default=[
            "doc_id",
            "disease",
            "symptoms",
            "antecedents",
            "severity",
            "description",
            "source",
        ],
        description="OpenSearch _source fields returned by retrieval queries",
    )
    INGEST_BATCH_SIZE: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of records to embed and bulk index per batch",
    )

    @property
    def models_dir(self) -> Path:
        return _resolve_project_path(self.PATH_TO_MODELS)

    @property
    def indices_dir(self) -> Path:
        return _resolve_project_path(self.PATH_TO_INDICES)

    @property
    def embedding_model_path(self) -> str:
        return str(self.models_dir / self.EMBEDDING_MODEL)

    @property
    def reranker_model_path(self) -> str:
        return str(self.models_dir / self.RERANKER_MODEL)


settings = Settings()
