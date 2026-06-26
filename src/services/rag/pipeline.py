"""RAG pipeline — preprocess, ingest, hybrid retrieve, and cross-encoder rerank."""

from src.db.vector_db.opensearch import OpenSearchClient, get_opensearch_client
from src.services.inference.embeddings.service import TextEmbeddingService
from src.services.inference.reranker.service import RerankerService
from src.services.rag.ingest import Ingestion
from src.services.rag.preprocess import PreprocessPipeline
from src.services.rag.retrieve import Retriever
from src.services.rag.schemas import DiseaseDocument, RetrieveResult
from src.settings import settings


class RAGService:
    """Production RAG entry point: shared preprocess, ingest, retrieve, rerank."""

    def __init__(
        self,
        client: OpenSearchClient | None = None,
        embed_service: TextEmbeddingService | None = None,
        rerank_service: RerankerService | None = None,
        *,
        preprocess: PreprocessPipeline | None = None,
        retriever: Retriever | None = None,
        ingestion: Ingestion | None = None,
    ) -> None:
        client = client or get_opensearch_client()
        embed_service = embed_service or TextEmbeddingService()
        rerank_service = rerank_service or RerankerService()
        preprocess_pipeline = preprocess or PreprocessPipeline()

        self.preprocess = preprocess_pipeline
        self.ingestion = ingestion or Ingestion(
            embed_service=embed_service,
            client=client,
        )
        self.retriever = retriever or Retriever(
            client=client,
            embed_service=embed_service,
            preprocess=preprocess_pipeline,
            rerank_service=rerank_service,
        )

    def ingest(
        self,
        records: list[DiseaseDocument],
        index_name: str | None = None,
    ) -> int:
        """Normalize, embed, and bulk-index disease records."""
        return self.ingestion.ingest(records, index_name=index_name)

    def query(self, user_query: str, index_name: str | None = None) -> RetrieveResult:
        """Run hybrid retrieval and rerank to the configured top_k."""
        result = self.retriever.retrieve(user_query, index_name=index_name)
        return self.retriever.rerank(user_query, result, top_k=settings.RERANK_TOP_K)
