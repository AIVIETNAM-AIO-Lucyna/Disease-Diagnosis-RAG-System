import os

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

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
        description="The path to the models",
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

    # PATH
    PATH_TO_INDICES: str = Field(
        default="indices",
        description="The path to the indices",
    )
    CURRENT_INDEX_MAPPING: str = Field(
        default="diseases/init_mapping.json",
        description="The path to the current index mapping",
    )
    CURRENT_SEARCH_PIPELINE: str = Field(
        default="hybrid-rrf",
        description="The name of the current search pipeline",
    )

    # Retrieval
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

    @property
    def embedding_model_path(self) -> str:
        return os.path.join(self.PATH_TO_MODELS, self.EMBEDDING_MODEL)


settings = Settings()
