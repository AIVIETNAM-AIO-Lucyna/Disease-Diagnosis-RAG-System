import os
import threading
from typing import ClassVar

from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer

from src.settings import settings

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class TextEmbeddingService:
    """Embed queries and documents using the configured text embedding model."""

    _model: ClassVar[SentenceTransformer | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def _embedding_model_path(cls) -> str:
        return settings.embedding_model_path

    @classmethod
    def download_embedding_model(cls) -> None:
        """Download the full embedding model repo if not present locally."""
        model_path = cls._embedding_model_path()
        model_marker = os.path.join(model_path, "config.json")
        if os.path.isfile(model_marker):
            return

        os.makedirs(model_path, exist_ok=True)
        snapshot_download(
            repo_id=settings.EMBEDDING_MODEL_REPO_ID,
            local_dir=model_path,
        )

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Return the shared SentenceTransformer instance (singleton)."""
        if cls._model is not None:
            return cls._model

        with cls._lock:
            if cls._model is None:
                cls.download_embedding_model()
                cls._model = SentenceTransformer(cls._embedding_model_path())
            return cls._model

    def embed_query(self, query: str) -> list[float]:
        return self.embed_queries([query])[0]

    def embed_queries(
        self, queries: list[str], *, batch_size: int = 64
    ) -> list[list[float]]:
        """Embed search queries with the BGE query prefix (batched, no progress bar)."""
        if not queries:
            return []

        model = self.get_model()
        vectors: list[list[float]] = []
        for start in range(0, len(queries), batch_size):
            batch = queries[start : start + batch_size]
            encoded = model.encode(
                batch,
                normalize_embeddings=True,
                prompt=BGE_QUERY_PREFIX,
                show_progress_bar=False,
            )
            vectors.extend(vector.tolist() for vector in encoded)
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self.get_model()
        vectors = model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return [vector.tolist() for vector in vectors]
