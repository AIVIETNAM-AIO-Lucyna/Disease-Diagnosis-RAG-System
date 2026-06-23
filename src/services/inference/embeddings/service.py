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
        model = self.get_model()
        vector = model.encode(
            [query], normalize_embeddings=True, prompt=BGE_QUERY_PREFIX
        )[0]
        return vector.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self.get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]
