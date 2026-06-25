"""Batch ingestion: normalize records, embed, and bulk index disease documents."""

from src.db.vector_db.opensearch import OpenSearchClient, get_opensearch_client
from src.services.inference.embeddings.service import TextEmbeddingService
from src.services.rag.preprocess import normalize_symptoms
from src.services.rag.schemas import BulkIngestRequest, DiseaseDocument
from src.settings import settings


class Ingestion:
    """Batch load, normalize, embed, and bulk index disease records."""

    def __init__(
        self,
        embed_service: TextEmbeddingService,
        client: OpenSearchClient | None = None,
        *,
        batch_size: int | None = None,
    ) -> None:
        self._embed_service = embed_service
        self._client = client or get_opensearch_client()
        self._batch_size = batch_size or settings.INGEST_BATCH_SIZE

    def ingest(
        self,
        records: list[DiseaseDocument],
        index_name: str | None = None,
    ) -> int:
        if not records:
            return 0

        target_index = index_name or settings.RETRIEVE_INDEX_ALIAS
        total = 0
        for start in range(0, len(records), self._batch_size):
            batch = records[start : start + self._batch_size]
            total += self._ingest_batch(batch, target_index)
        return total

    def _ingest_batch(self, records: list[DiseaseDocument], index_name: str) -> int:
        normalized_records = [self._normalize_record(record) for record in records]
        embed_texts = [record.embed_text for record in normalized_records]
        embeddings = self._embed_service.embed_documents(embed_texts)

        documents = [
            record.model_copy(update={"embedding": embedding})
            for record, embedding in zip(normalized_records, embeddings, strict=True)
        ]

        request = BulkIngestRequest(index_name=index_name, documents=documents)
        self._client.bulk(request.to_bulk_actions())
        return len(documents)

    @staticmethod
    def _normalize_record(record: DiseaseDocument) -> DiseaseDocument:
        return record.model_copy(
            update={
                "symptoms": normalize_symptoms(record.symptoms),
                "antecedents": normalize_symptoms(record.antecedents),
            }
        )
