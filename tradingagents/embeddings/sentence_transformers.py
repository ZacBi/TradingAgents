# TradingAgents/embeddings/sentence_transformers.py
"""Sentence Transformers embedding provider (local, no API cost)."""

import logging
from typing import Optional

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "sentence-transformers not installed. "
        "Install with: pip install sentence-transformers"
    )


class SentenceTransformersProvider(EmbeddingProvider):
    """
    Local embedding provider using Sentence Transformers.
    
    Default model: all-MiniLM-L6-v2 (fast, 384 dimensions)
    Alternative: all-mpnet-base-v2 (better quality, 768 dimensions)
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
    ):
        """
        Initialize the Sentence Transformers provider.
        
        Args:
            model_name: Name of the sentence-transformers model
            device: Device to run on ('cpu', 'cuda', 'mps', or None for auto)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required. "
                "Install with: pip install sentence-transformers"
            )
        
        self._model_name = model_name
        self._model = SentenceTransformer(model_name, device=device)
        self._dimension = self._model.get_sentence_embedding_dimension()
        
        logger.info(
            "Initialized SentenceTransformers with model=%s, dim=%d",
            model_name, self._dimension
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embedding = self._model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embedding.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name


def create_sentence_transformers_provider(
    config: dict,
) -> Optional[SentenceTransformersProvider]:
    """
    Factory function to create a SentenceTransformers provider.
    
    Args:
        config: Configuration dictionary with optional keys:
            - embedding_model: Model name (default: all-MiniLM-L6-v2)
            
    Returns:
        Provider instance or None if not available
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None
    
    model_name = config.get("embedding_model", "all-MiniLM-L6-v2")
    return SentenceTransformersProvider(model_name=model_name)
