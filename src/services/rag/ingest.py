"""Ingestion — not implemented (owned by another developer).


When implemented, use ``DiseaseDocument`` / ``BulkIngestRequest`` to build bulk
actions and call ``OpenSearchClient.bulk()``.
"""

from typing import Any

from pydantic import Field, model_validator

from src.schemas.base import RWSBaseModel
from src.settings import settings

from src.db.vector_db.opensearch import (
    OpenSearchClient,
    get_opensearch_client,
)
from src.services.ai_inference.bge.service import BGEInferenceService

"""
When implemented, refactor those schemas to schemas.py
"""


class DiseaseDocument(RWSBaseModel):
    """OpenSearch disease document for idempotent bulk upsert."""

    doc_id: str = Field(..., min_length=1)
    disease: str = Field(..., min_length=1)
    symptoms: list[str]
    antecedents: list[str] = Field(default_factory=list)
    keyword_text: str = Field(..., min_length=1)
    embedding: list[float]
    severity: int = Field(..., ge=1, le=5)
    description: str = ""
    source: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_embedding_dimension(self) -> "DiseaseDocument":
        if len(self.embedding) != 384:
            msg = f"embedding must be 384-dimensional, got {len(self.embedding)}"
            raise ValueError(msg)
        return self

    def to_bulk_action(self, index_name: str) -> dict[str, Any]:
        """Build one OpenSearch bulk index line with ``_id = doc_id``."""
        return {"_index": index_name, "_id": self.doc_id, **self.to_dict()}


class BulkIngestRequest(RWSBaseModel):
    """Bulk upsert request for disease documents."""

    index_name: str = Field(default_factory=lambda: settings.RETRIEVE_INDEX_ALIAS)
    documents: list[DiseaseDocument] = Field(..., min_length=1)

    def to_bulk_actions(self) -> list[dict[str, Any]]:
        """Convert documents to OpenSearch bulk action dicts."""
        return [doc.to_bulk_action(self.index_name) for doc in self.documents]


class Ingestion:
    """Batch load, normalize, embed, and bulk index disease records."""

    def __init__(
        self,
        embed_service: BGEInferenceService,
        client: OpenSearchClient | None = None,
    ) -> None:
        self._embed_service = embed_service
        self._client = client or get_opensearch_client()

    def ingest(
        self,
        records: list[dict[str, Any]],
        index_name: str | None = None,
    ) -> int:
        if not records:
            return 0

        embed_texts = [
            self._build_embed_text(
                disease=record["disease"],
                symptoms=record["symptoms"],
                description=record.get("description", ""),
            )
            for record in records
        ]

        embeddings = self._embed_service.embed_documents(embed_texts)

        documents = [
            self._build_document(record, embedding)
            for record, embedding in zip(
                records,
                embeddings,
            )
        ]

        request = BulkIngestRequest(
            index_name=index_name or settings.RETRIEVE_INDEX_ALIAS,
            documents=documents,
        )

        self._client.bulk(request.to_bulk_actions())

        return len(documents)

    @staticmethod
    def _build_embed_text(
        disease: str,
        symptoms: list[str],
        description: str,
    ) -> str:
        symptom_str = ", ".join(symptoms)

        return f"Disease: {disease}. " f"Symptoms: {symptom_str}. " f"{description}"

    REQUIRED_FIELDS = (
        "doc_id",
        "disease",
        "symptoms",
        "keyword_text",
        "severity",
        "source",
    )

    def _build_document(
        self,
        record: dict[str, Any],
        embedding: list[float],
    ) -> DiseaseDocument:
        missing_fields = [
            field for field in self.REQUIRED_FIELDS if field not in record
        ]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        return DiseaseDocument(
            doc_id=record["doc_id"],
            disease=record["disease"],
            symptoms=record["symptoms"],
            antecedents=record.get("antecedents", []),
            keyword_text=record["keyword_text"],
            embedding=embedding,
            severity=record["severity"],
            description=record.get("description", ""),
            source=record["source"],
        )
