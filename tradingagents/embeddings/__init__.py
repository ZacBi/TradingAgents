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
from typing import Optional

from .base import EmbeddingProvider
from .sentence_transformers import (
    SentenceTransformersProvider,
    create_sentence_transformers_provider,
    SENTENCE_TRANSFORMERS_AVAILABLE,
)
from .openai import (
    OpenAIEmbeddingProvider,
    create_openai_embedding_provider,
    OPENAI_AVAILABLE,
)
from .google import (
    GoogleEmbeddingProvider,
    create_google_embedding_provider,
    GOOGLE_AVAILABLE,
)
from .litellm import (
    LiteLLMEmbeddingProvider,
    create_litellm_embedding_provider,
    LITELLM_AVAILABLE,
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


def create_embedding_provider(config: dict) -> Optional[EmbeddingProvider]:
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
    
    # Try to create the requested provider
    provider = None
    
    if provider_name == "sentence_transformers":
        provider = create_sentence_transformers_provider(config)
    elif provider_name == "openai":
        provider = create_openai_embedding_provider(config)
    elif provider_name == "google":
        provider = create_google_embedding_provider(config)
    elif provider_name == "litellm":
        provider = create_litellm_embedding_provider(config)
    else:
        logger.warning("Unknown embedding provider: %s", provider_name)
    
    # If requested provider failed, try fallbacks
    if provider is None:
        logger.warning(
            "Failed to create %s provider, trying fallbacks", provider_name
        )
        
        # Try sentence_transformers first (free, local)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            provider = create_sentence_transformers_provider(config)
            if provider:
                logger.info("Fell back to sentence_transformers")
                return provider
        
        # Try LiteLLM
        if LITELLM_AVAILABLE:
            provider = create_litellm_embedding_provider(config)
            if provider:
                logger.info("Fell back to litellm")
                return provider
        
        # Try OpenAI
        if OPENAI_AVAILABLE:
            provider = create_openai_embedding_provider(config)
            if provider:
                logger.info("Fell back to openai")
                return provider
        
        # Try Google
        if GOOGLE_AVAILABLE:
            provider = create_google_embedding_provider(config)
            if provider:
                logger.info("Fell back to google")
                return provider
        
        logger.error("No embedding provider available")
        return None
    
    return provider
