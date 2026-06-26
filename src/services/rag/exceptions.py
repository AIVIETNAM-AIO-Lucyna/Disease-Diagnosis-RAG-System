from src.schemas.base import CustomException


class RerankerNotConfigured(CustomException):
    """Exception raised when the reranker is not configured."""

    message = "Reranker is not configured"
