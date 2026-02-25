# TradingAgents/embeddings/__init__.py
"""
Embedding providers for debate convergence detection.

Supports multiple providers:
- sentence_transformers: Local, no API cost (default)
- openai: OpenAI text-embedding-3-small/large
- google: Google text-embedding-004
- litellm: Unified interface for multiple providers
"""

import logging

from .base import EmbeddingProvider
from .google import (
    GOOGLE_AVAILABLE,
    GoogleEmbeddingProvider,
    create_google_embedding_provider,
)
from .litellm import (
    LITELLM_AVAILABLE,
    LiteLLMEmbeddingProvider,
    create_litellm_embedding_provider,
)
from .openai import (
    OPENAI_AVAILABLE,
    OpenAIEmbeddingProvider,
    create_openai_embedding_provider,
)
from .sentence_transformers import (
    SENTENCE_TRANSFORMERS_AVAILABLE,
    SentenceTransformersProvider,
    create_sentence_transformers_provider,
)

logger = logging.getLogger(__name__)

__all__ = [
    "EmbeddingProvider",
    "SentenceTransformersProvider",
    "OpenAIEmbeddingProvider",
    "GoogleEmbeddingProvider",
    "LiteLLMEmbeddingProvider",
    "create_embedding_provider",
    "SENTENCE_TRANSFORMERS_AVAILABLE",
    "OPENAI_AVAILABLE",
    "GOOGLE_AVAILABLE",
    "LITELLM_AVAILABLE",
]


_EMBEDDING_CREATORS = {
    "sentence_transformers": create_sentence_transformers_provider,
    "openai": create_openai_embedding_provider,
    "google": create_google_embedding_provider,
    "litellm": create_litellm_embedding_provider,
}

_FALLBACK_ORDER = [
    ("sentence_transformers", SENTENCE_TRANSFORMERS_AVAILABLE, create_sentence_transformers_provider),
    ("litellm", LITELLM_AVAILABLE, create_litellm_embedding_provider),
    ("openai", OPENAI_AVAILABLE, create_openai_embedding_provider),
    ("google", GOOGLE_AVAILABLE, create_google_embedding_provider),
]


def _try_create_provider(config: dict, name: str):
    """Create provider by name; return instance or None."""
    creator = _EMBEDDING_CREATORS.get(name)
    if creator is None:
        logger.warning("Unknown embedding provider: %s", name)
        return None
    return creator(config)


def create_embedding_provider(config: dict) -> EmbeddingProvider | None:
    """
    Factory function to create an embedding provider based on configuration.

    Args:
        config: Configuration dictionary with keys:
            - embedding_provider: Provider name
              ("sentence_transformers", "openai", "google", "litellm")
            - embedding_model: Model name (provider-specific)

    Returns:
        EmbeddingProvider instance or None if creation fails

    Provider priority (if specified provider fails):
    1. sentence_transformers (local, no cost)
    2. litellm (if available)
    3. openai
    4. google
    """
    provider_name = config.get("embedding_provider", "sentence_transformers")
    provider = _try_create_provider(config, provider_name)
    if provider is not None:
        return provider

    logger.warning("Failed to create %s provider, trying fallbacks", provider_name)
    for name, available, creator in _FALLBACK_ORDER:
        if not available:
            continue
        provider = creator(config)
        if provider is not None:
            logger.info("Fell back to %s", name)
            return provider
    logger.error("No embedding provider available")
    return None
