"""RAG pipeline — hybrid retrieve and cross-encoder rerank."""

from src.db.vector_db.opensearch import OpenSearchClient, get_opensearch_client
from src.services.inference.embeddings.service import TextEmbeddingService
from src.services.inference.reranker.service import RerankerService
from src.services.rag.retrieve import Retriever
from src.services.rag.schemas import RetrieveResult
from src.settings import settings


class RAGService:
    """Production RAG entry point: hybrid retrieve then cross-encoder rerank."""

    def __init__(
        self,
        client: OpenSearchClient | None = None,
        embed_service: TextEmbeddingService | None = None,
        rerank_service: RerankerService | None = None,
        *,
        retriever: Retriever | None = None,
    ) -> None:
        client = client or get_opensearch_client()
        embed_service = embed_service or TextEmbeddingService()
        rerank_service = rerank_service or RerankerService()
        self.retriever = retriever or Retriever(
            embed_service=embed_service,
            client=client,
            rerank_service=rerank_service,
        )

    def query(self, user_query: str, index_name: str | None = None) -> RetrieveResult:
        """Run hybrid retrieval and rerank to the configured top_k."""
        result = self.retriever.retrieve(user_query, index_name=index_name)
        return self.retriever.rerank(user_query, result, top_k=settings.RERANK_TOP_K)
