import os
import threading
from typing import ClassVar

from huggingface_hub import snapshot_download
from sentence_transformers import CrossEncoder

from src.settings import settings


class RerankerService:
    """Cross-encoder reranking using the configured reranker model."""

    _model: ClassVar[CrossEncoder | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def _reranker_model_path(cls) -> str:
        return settings.reranker_model_path

    @classmethod
    def download_reranker_model(cls) -> None:
        """Download the full reranker model repo if not present locally."""
        model_path = cls._reranker_model_path()
        model_marker = os.path.join(model_path, "config.json")
        if os.path.isfile(model_marker):
            return

        os.makedirs(model_path, exist_ok=True)
        snapshot_download(
            repo_id=settings.RERANKER_MODEL_REPO_ID,
            local_dir=model_path,
        )

    @classmethod
    def get_model(cls) -> CrossEncoder:
        """Return the shared CrossEncoder instance (singleton)."""
        if cls._model is not None:
            return cls._model

        with cls._lock:
            if cls._model is None:
                cls.download_reranker_model()
                cls._model = CrossEncoder(cls._reranker_model_path())
            return cls._model

    def rerank(
        self,
        query: str,
        passages: list[str],
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        """Score query-passage pairs and return ranked (index, score) tuples."""
        if not passages:
            return []

        model = self.get_model()
        pairs = [(query, passage) for passage in passages]
        raw_scores = model.predict(pairs)

        ranked = sorted(
            ((index, float(score)) for index, score in enumerate(raw_scores)),
            key=lambda item: item[1],
            reverse=True,
        )

        if top_k is not None:
            ranked = ranked[:top_k]

        return ranked
