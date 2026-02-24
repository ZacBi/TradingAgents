# TradingAgents/embeddings/google.py
"""Google (Gemini) embedding provider."""

import logging
import os
from typing import Optional

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GoogleEmbeddingProvider(EmbeddingProvider):
    """
    Google embedding provider using Gemini embedding models.
    
    Models:
    - text-embedding-004: Latest, 768 dimensions
    - embedding-001: Legacy
    """

    MODEL_DIMENSIONS = {
        "text-embedding-004": 768,
        "embedding-001": 768,
    }

    def __init__(
        self,
        model_name: str = "text-embedding-004",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Google embedding provider.
        
        Args:
            model_name: Name of the Google embedding model
            api_key: Google API key (or uses GOOGLE_API_KEY env var)
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "google-generativeai package is required. "
                "Install with: pip install google-generativeai"
            )
        
        self._model_name = model_name
        self._dimension = self.MODEL_DIMENSIONS.get(model_name, 768)
        
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API key is required")
        
        genai.configure(api_key=api_key)
        
        logger.info(
            "Initialized Google embeddings with model=%s, dim=%d",
            model_name, self._dimension
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model=f"models/{self._model_name}",
                content=text,
                task_type="retrieval_document",
            )
            embeddings.append(result["embedding"])
        return embeddings

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        result = genai.embed_content(
            model=f"models/{self._model_name}",
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name


def create_google_embedding_provider(
    config: dict,
) -> Optional[GoogleEmbeddingProvider]:
    """
    Factory function to create a Google embedding provider.
    
    Args:
        config: Configuration dictionary with optional keys:
            - embedding_model: Model name (default: text-embedding-004)
            - google_api_key: API key
            
    Returns:
        Provider instance or None if not available
    """
    if not GOOGLE_AVAILABLE:
        return None
    
    model_name = config.get("embedding_model", "text-embedding-004")
    api_key = config.get("google_api_key")
    
    try:
        return GoogleEmbeddingProvider(model_name=model_name, api_key=api_key)
    except (ImportError, ValueError) as e:
        logger.warning("Failed to create Google embedding provider: %s", e)
        return None
