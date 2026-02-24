# TradingAgents/embeddings/openai.py
"""OpenAI embedding provider."""

import logging
import os
from typing import Optional

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3-small/large.
    
    Models:
    - text-embedding-3-small: 1536 dimensions, cheaper
    - text-embedding-3-large: 3072 dimensions, better quality
    - text-embedding-ada-002: 1536 dimensions (legacy)
    """

    # Model dimensions
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the OpenAI embedding provider.
        
        Args:
            model_name: Name of the OpenAI embedding model
            api_key: OpenAI API key (or uses OPENAI_API_KEY env var)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )
        
        self._model_name = model_name
        self._dimension = self.MODEL_DIMENSIONS.get(model_name, 1536)
        
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self._client = OpenAI(api_key=api_key)
        
        logger.info(
            "Initialized OpenAI embeddings with model=%s, dim=%d",
            model_name, self._dimension
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = self._client.embeddings.create(
            model=self._model_name,
            input=texts,
        )
        return [data.embedding for data in response.data]

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = self._client.embeddings.create(
            model=self._model_name,
            input=[text],
        )
        return response.data[0].embedding

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name


def create_openai_embedding_provider(
    config: dict,
) -> Optional[OpenAIEmbeddingProvider]:
    """
    Factory function to create an OpenAI embedding provider.
    
    Args:
        config: Configuration dictionary with optional keys:
            - embedding_model: Model name (default: text-embedding-3-small)
            - openai_api_key: API key
            
    Returns:
        Provider instance or None if not available
    """
    if not OPENAI_AVAILABLE:
        return None
    
    model_name = config.get("embedding_model", "text-embedding-3-small")
    api_key = config.get("openai_api_key")
    
    try:
        return OpenAIEmbeddingProvider(model_name=model_name, api_key=api_key)
    except (ImportError, ValueError) as e:
        logger.warning("Failed to create OpenAI embedding provider: %s", e)
        return None
