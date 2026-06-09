"""Ingestion — not implemented (owned by another developer).


When implemented, use ``DiseaseDocument`` / ``BulkIngestRequest`` to build bulk
actions and call ``OpenSearchClient.bulk()``.
"""

from typing import Any

from pydantic import Field, model_validator

from src.schemas.base import RWSBaseModel
from src.settings import settings

"""
When implemented, refactor those schemas to schemas.py
"""


class DiseaseDocument(RWSBaseModel):
    """OpenSearch disease document for idempotent bulk upsert."""

    doc_id: str = Field(..., min_length=1)
    disease: str = Field(..., min_length=1)
    symptoms: list[str]
    keyword_text: str = Field(..., min_length=1)
    embedding: list[float]
    severity: str | None = None
    description: str = ""
    precautions: list[str] | str | None = None

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

    def ingest(
        self,
        records: list[dict[str, Any]],
        index_name: str | None = None,
    ) -> int:
        raise NotImplementedError("Ingestion is not implemented in this branch. ")
