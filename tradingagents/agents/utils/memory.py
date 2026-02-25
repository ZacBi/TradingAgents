"""Financial situation memory using LangGraph Store for semantic similarity matching.

Uses LangGraph's BaseStore API with OpenAI embeddings for semantic retrieval.
Supports both InMemoryStore (development) and PostgresStore (production).
"""

import logging
import uuid
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


class FinancialSituationMemory:
    """Memory system for storing and retrieving financial situations using LangGraph Store.

    This class wraps LangGraph's BaseStore API to provide semantic similarity search
    for financial situations and their corresponding recommendations.
    """

    def __init__(
        self,
        name: str,
        store: Optional[Any] = None,
        embedder: Optional[Callable[[str], List[float]]] = None,
    ):
        """Initialize the memory system.

        Args:
            name: Name identifier for this memory instance (used as namespace).
            store: LangGraph BaseStore instance (InMemoryStore or PostgresStore).
            embedder: Callable that converts text to embedding vector.
        """
        self.name = name
        self.store = store
        self.embedder = embedder
        self._namespace = ("memories", name)

        # Track if store is available
        self._store_available = store is not None and embedder is not None

        if not self._store_available:
            logger.warning(
                "FinancialSituationMemory '%s' initialized without store/embedder. "
                "Memory operations will be no-ops.",
                name,
            )

    def add_situations(self, situations_and_advice: List[tuple[str, str]]) -> None:
        """Add financial situations and their corresponding advice.

        Args:
            situations_and_advice: List of tuples (situation, recommendation).
        """
        if not self._store_available:
            return

        for situation, recommendation in situations_and_advice:
            try:
                memory_id = str(uuid.uuid4())
                value = {
                    "situation": situation,
                    "recommendation": recommendation,
                }
                self.store.put(self._namespace, memory_id, value)
                logger.debug(
                    "Added memory to '%s': %s...",
                    self.name,
                    situation[:50],
                )
            except Exception as e:
                logger.error("Failed to add memory to '%s': %s", self.name, e)

    def get_memories(self, current_situation: str, n_matches: int = 1) -> List[dict]:
        """Find matching recommendations using semantic similarity.

        Args:
            current_situation: The current financial situation to match against.
            n_matches: Number of top matches to return.

        Returns:
            List of dicts with matched_situation, recommendation, and similarity_score.
        """
        if not self._store_available:
            return []

        try:
            # Use LangGraph Store's search API with semantic matching
            results = self.store.search(
                self._namespace,
                query=current_situation,
                limit=n_matches,
            )

            # Convert to legacy format for compatibility
            memories = []
            for item in results:
                value = item.value
                # LangGraph Store returns score as item.score (0-1 range)
                score = getattr(item, "score", 0.5)
                memories.append({
                    "matched_situation": value.get("situation", ""),
                    "recommendation": value.get("recommendation", ""),
                    "similarity_score": score,
                })

            return memories

        except Exception as e:
            logger.error("Failed to search memories in '%s': %s", self.name, e)
            return []

    def clear(self) -> None:
        """Clear all stored memories.

        Note: LangGraph Store doesn't have a native clear method.
        This is a no-op for now; memories persist until explicitly deleted.
        """
        logger.warning(
            "clear() called on '%s' but LangGraph Store doesn't support bulk delete. "
            "Memories will persist.",
            self.name,
        )


def create_memory_store(config: dict) -> Optional[Any]:
    """Create a LangGraph Store based on configuration.

    Args:
        config: Configuration dict with store_enabled, store_backend, etc.

    Returns:
        LangGraph BaseStore instance or None if disabled.
    """
    if not config.get("store_enabled", True):
        logger.info("LangGraph Store disabled by configuration.")
        return None

    backend = config.get("store_backend", "memory")

    try:
        if backend == "memory":
            from langgraph.store.memory import InMemoryStore

            # Get embedding configuration
            embedder = create_embedder(config)
            if embedder is None:
                # Create store without indexing (no semantic search)
                store = InMemoryStore()
                logger.info("Created InMemoryStore without semantic indexing.")
            else:
                # Create store with semantic indexing
                dims = config.get("store_embedding_dimension", 1536)
                store = InMemoryStore(
                    index={
                        "embed": embedder,
                        "dims": dims,
                    }
                )
                logger.info("Created InMemoryStore with semantic indexing (dims=%d).", dims)
            return store

        elif backend == "postgres":
            from langgraph.store.postgres import PostgresStore

            # Get PostgreSQL URL (prefer unified, fallback to store-specific)
            pg_url = config.get("postgres_url") or config.get("store_postgres_url")
            if not pg_url:
                logger.error("PostgreSQL URL not configured for store backend.")
                return None

            # Get embedding configuration
            embedder = create_embedder(config)
            dims = config.get("store_embedding_dimension", 1536)

            if embedder is None:
                store = PostgresStore.from_conn_string(pg_url)
            else:
                store = PostgresStore.from_conn_string(
                    pg_url,
                    index={
                        "embed": embedder,
                        "dims": dims,
                    },
                )
            logger.info("Created PostgresStore with semantic indexing.")
            return store

        else:
            logger.error("Unknown store_backend: %s", backend)
            return None

    except ImportError as e:
        logger.error("Failed to import store backend '%s': %s", backend, e)
        return None
    except Exception as e:
        logger.error("Failed to create store backend '%s': %s", backend, e)
        return None


def create_embedder(config: dict) -> Optional[Callable[[str], List[float]]]:
    """Create an embedding function based on configuration.

    Args:
        config: Configuration dict with store_embedding_provider, store_embedding_model.

    Returns:
        Callable that converts text to embedding vector, or None.
    """
    provider = config.get("store_embedding_provider", "openai")
    model = config.get("store_embedding_model", "text-embedding-3-small")

    try:
        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(model=model)
            logger.info("Created OpenAI embedder with model '%s'.", model)
            return embeddings

        elif provider == "sentence_transformers":
            from langchain_community.embeddings import HuggingFaceEmbeddings

            embeddings = HuggingFaceEmbeddings(model_name=model)
            logger.info("Created SentenceTransformers embedder with model '%s'.", model)
            return embeddings

        else:
            logger.warning("Unknown embedding provider: %s", provider)
            return None

    except ImportError as e:
        logger.error("Failed to import embedder for '%s': %s", provider, e)
        return None
    except Exception as e:
        logger.error("Failed to create embedder for '%s': %s", provider, e)
        return None


if __name__ == "__main__":
    # Example usage with InMemoryStore
    from tradingagents.default_config import DEFAULT_CONFIG

    config = DEFAULT_CONFIG.copy()
    config["store_backend"] = "memory"
    config["store_embedding_provider"] = "openai"

    store = create_memory_store(config)
    embedder = create_embedder(config)

    matcher = FinancialSituationMemory("test_memory", store, embedder)

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling",
            "Reduce exposure to high-growth tech stocks.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions.",
        ),
    ]

    matcher.add_situations(example_data)

    # Query
    current_situation = "Market showing increased volatility in tech sector"
    recommendations = matcher.get_memories(current_situation, n_matches=2)

    for i, rec in enumerate(recommendations, 1):
        print(f"\nMatch {i}:")
        print(f"Similarity Score: {rec['similarity_score']:.2f}")
        print(f"Matched Situation: {rec['matched_situation']}")
        print(f"Recommendation: {rec['recommendation']}")
