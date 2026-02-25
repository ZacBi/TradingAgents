# TradingAgents/embeddings/litellm.py
"""LiteLLM unified embedding provider."""

import logging

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class LiteLLMEmbeddingProvider(EmbeddingProvider):
    """
    LiteLLM unified embedding provider.

    Supports multiple providers through LiteLLM's unified interface:
    - openai/text-embedding-3-small
    - google/text-embedding-004
    - cohere/embed-english-v3.0
    - etc.
    """

    def __init__(
        self,
        model_name: str = "openai/text-embedding-3-small",
        dimension: int = 1536,
    ):
        """
        Initialize the LiteLLM embedding provider.

        Args:
            model_name: Model in LiteLLM format (provider/model)
            dimension: Expected embedding dimension
        """
        if not LITELLM_AVAILABLE:
            raise ImportError(
                "litellm package is required. Install with: pip install litellm"
            )

        self._model_name = model_name
        self._dimension = dimension

        logger.info(
            "Initialized LiteLLM embeddings with model=%s, dim=%d",
            model_name, dimension
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = litellm.embedding(
            model=self._model_name,
            input=texts,
        )
        return [data["embedding"] for data in response.data]

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = litellm.embedding(
            model=self._model_name,
            input=[text],
        )
        return response.data[0]["embedding"]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name


def create_litellm_embedding_provider(
    config: dict,
) -> LiteLLMEmbeddingProvider | None:
    """
    Factory function to create a LiteLLM embedding provider.

    Args:
        config: Configuration dictionary with keys:
            - embedding_model: Model in LiteLLM format
            - embedding_dimension: Expected dimension (default: 1536)

    Returns:
        Provider instance or None if not available
    """
    if not LITELLM_AVAILABLE:
        return None

    model_name = config.get("embedding_model", "openai/text-embedding-3-small")
    dimension = config.get("embedding_dimension", 1536)

    try:
        return LiteLLMEmbeddingProvider(model_name=model_name, dimension=dimension)
    except ImportError as e:
        logger.warning("Failed to create LiteLLM embedding provider: %s", e)
        return None
