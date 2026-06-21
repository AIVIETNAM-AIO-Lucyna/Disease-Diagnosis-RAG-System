"""Ingestion — not implemented (owned by another developer).


When implemented, use ``DiseaseDocument`` / ``BulkIngestRequest`` to build bulk
actions and call ``OpenSearchClient.bulk()``.
"""

from src.settings import settings

from src.db.vector_db.opensearch import (
    OpenSearchClient,
    get_opensearch_client,
)
from src.services.ai_inference.bge.service import BGEInferenceService

from src.services.rag.schemas import (
    IngestRecord,
    DiseaseDocument,
    BulkIngestRequest,
)


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
        records: list[IngestRecord],
        index_name: str | None = None,
    ) -> int:
        if not records:
            return 0

        embed_texts = [
            self._build_embed_text(
                disease=record.disease,
                symptoms=record.symptoms,
                description=record.description,
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

    def _build_document(
        self,
        record: IngestRecord,
        embedding: list[float],
    ) -> DiseaseDocument:
        return DiseaseDocument(
            doc_id=record.doc_id,
            disease=record.disease,
            symptoms=record.symptoms,
            antecedents=record.antecedents,
            keyword_text=record.keyword_text,
            embedding=embedding,
            severity=record.severity,
            description=record.description,
            source=record.source,
        )
