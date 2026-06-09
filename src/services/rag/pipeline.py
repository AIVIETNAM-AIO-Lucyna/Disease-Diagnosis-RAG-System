"""Retrieval facade — full RAG orchestration is owned by other developers."""

from src.db.vector_db.opensearch import OpenSearchClient, get_opensearch_client
from src.services.ai_inference.bge.service import BGEInferenceService
from src.services.rag.retrieve import Retriever
from src.services.rag.schemas import RetrieveResult


class RAGService:
    """Retrieval-only entry point until rerank/generate/API land."""

    def __init__(
        self,
        client: OpenSearchClient | None = None,
        embed_service: BGEInferenceService | None = None,
        *,
        retriever: Retriever | None = None,
    ) -> None:
        client = client or get_opensearch_client()
        embed_service = embed_service or BGEInferenceService()
        self.retriever = retriever or Retriever(
            embed_service=embed_service, client=client
        )

    def query(self, user_query: str, index_name: str | None = None) -> RetrieveResult:
        """Run hybrid retrieval for a user symptom query."""
        return self.retriever.retrieve(user_query, index_name=index_name)
