"""RAG service package — retrieval implemented; other stages owned separately."""

from src.services.rag.pipeline import RAGService
from src.services.rag.preprocess import preprocess_query
from src.services.rag.retrieve import Retriever
from src.services.rag.schemas import IngestRecord

__all__ = [
    "RAGService",
    "Retriever",
    "preprocess_query",
    "IngestRecord",
]
