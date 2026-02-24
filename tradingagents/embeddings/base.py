# TradingAgents/embeddings/base.py
"""Base class for embedding providers."""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    
    Provides text embedding and similarity computation capabilities
    for debate convergence detection.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each as list of floats)
        """
        pass

    @abstractmethod
    def embed_single(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector as list of floats
        """
        pass

    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        emb1 = self.embed_single(text1)
        emb2 = self.embed_single(text2)
        return self._cosine_similarity(emb1, emb2)

    def batch_similarity(self, texts: list[str]) -> list[float]:
        """
        Compute pairwise similarities between consecutive texts.
        
        Args:
            texts: List of texts
            
        Returns:
            List of similarity scores between consecutive pairs
        """
        if len(texts) < 2:
            return []
        
        embeddings = self.embed(texts)
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)
        return similarities

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of embeddings produced by this provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the embedding model."""
        pass
