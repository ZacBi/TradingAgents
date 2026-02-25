# TradingAgents/graph/convergence.py
"""Dynamic convergence detection for debate mechanisms."""

import logging

from tradingagents.embeddings import EmbeddingProvider, create_embedding_provider

logger = logging.getLogger(__name__)


class ConvergenceDetector:
    """
    Detects when debates have converged semantically.

    Uses embedding similarity to determine if consecutive debate rounds
    are producing diminishing information gains.
    """

    def __init__(self, config: dict):
        """
        Initialize the convergence detector.

        Args:
            config: Configuration dictionary with keys:
                - debate_convergence_enabled: Whether to use semantic convergence
                - debate_semantic_threshold: Similarity threshold (default: 0.85)
                - debate_info_gain_threshold: Min info gain (default: 0.1)
                - max_debate_rounds: Hard maximum rounds (default: 3)
                - embedding_provider: Provider for embeddings
        """
        self.enabled = config.get("debate_convergence_enabled", True)
        self.semantic_threshold = config.get("debate_semantic_threshold", 0.85)
        self.info_gain_threshold = config.get("debate_info_gain_threshold", 0.1)
        self.max_rounds = config.get("max_debate_rounds", 3)

        # Initialize embedding provider if convergence is enabled
        self._embedding_provider: EmbeddingProvider | None = None
        if self.enabled:
            try:
                self._embedding_provider = create_embedding_provider(config)
                if self._embedding_provider:
                    logger.info(
                        "Convergence detector initialized with %s embeddings",
                        self._embedding_provider.model_name
                    )
                else:
                    logger.warning(
                        "No embedding provider available, "
                        "falling back to round-based convergence"
                    )
                    self.enabled = False
            except Exception as e:
                logger.warning(
                    "Failed to initialize embedding provider: %s. "
                    "Falling back to round-based convergence.", e
                )
                self.enabled = False

    def should_stop(
        self,
        history: list[str],
        current_round: int,
    ) -> tuple[bool, str]:
        """
        Determine if the debate should stop.

        Args:
            history: List of debate arguments (alternating speakers)
            current_round: Current debate round number

        Returns:
            Tuple of (should_stop, reason)
            reason: "max_rounds" | "semantic_converged" | "info_gain_low" | "continue"
        """
        # Hard limit on rounds
        if current_round >= self.max_rounds * 2:  # 2 speakers per round
            return True, "max_rounds"

        # Need at least 4 entries (2 full rounds) for convergence detection
        if len(history) < 4:
            return False, "continue"

        # If semantic convergence is disabled, only use round limit
        if not self.enabled or self._embedding_provider is None:
            return False, "continue"

        # Check semantic convergence
        try:
            converged, reason = self._check_semantic_convergence(history)
            if converged:
                return True, reason
        except Exception as e:
            logger.warning("Convergence check failed: %s", e)

        return False, "continue"

    def _check_semantic_convergence(
        self,
        history: list[str],
    ) -> tuple[bool, str]:
        """
        Check if debate has semantically converged.

        Compares the last two rounds to see if they're too similar.
        """
        if len(history) < 4:
            return False, "continue"

        # Get the last two complete rounds
        # For a 2-speaker debate: [bull1, bear1, bull2, bear2]
        # Compare bull1+bear1 vs bull2+bear2
        prev_round = " ".join(history[-4:-2])  # Previous round
        curr_round = " ".join(history[-2:])    # Current round

        similarity = self._embedding_provider.similarity(prev_round, curr_round)

        logger.debug(
            "Debate convergence check: similarity=%.3f, threshold=%.3f",
            similarity, self.semantic_threshold
        )

        if similarity >= self.semantic_threshold:
            logger.info(
                "Debate converged semantically (similarity=%.3f)", similarity
            )
            return True, "semantic_converged"

        # Check information gain (simple heuristic: new unique words)
        prev_words = set(prev_round.lower().split())
        curr_words = set(curr_round.lower().split())
        new_words = curr_words - prev_words

        if len(curr_words) > 0:
            info_gain = len(new_words) / len(curr_words)

            logger.debug(
                "Debate info gain: %.3f, threshold: %.3f",
                info_gain, self.info_gain_threshold
            )

            if info_gain < self.info_gain_threshold:
                logger.info(
                    "Debate stopped due to low info gain (%.3f)", info_gain
                )
                return True, "info_gain_low"

        return False, "continue"

    def get_convergence_metrics(
        self,
        history: list[str],
    ) -> dict:
        """
        Get detailed convergence metrics for debugging/logging.

        Args:
            history: List of debate arguments

        Returns:
            Dictionary with convergence metrics
        """
        metrics = {
            "round_count": len(history) // 2,
            "max_rounds": self.max_rounds,
            "convergence_enabled": self.enabled,
            "semantic_similarity": None,
            "info_gain": None,
        }

        if not self.enabled or self._embedding_provider is None:
            return metrics

        if len(history) >= 4:
            try:
                prev_round = " ".join(history[-4:-2])
                curr_round = " ".join(history[-2:])

                metrics["semantic_similarity"] = self._embedding_provider.similarity(
                    prev_round, curr_round
                )

                prev_words = set(prev_round.lower().split())
                curr_words = set(curr_round.lower().split())
                new_words = curr_words - prev_words

                if len(curr_words) > 0:
                    metrics["info_gain"] = len(new_words) / len(curr_words)
            except Exception as e:
                logger.warning("Failed to compute metrics: %s", e)

        return metrics


def create_convergence_detector(config: dict) -> ConvergenceDetector:
    """Factory function to create a convergence detector."""
    return ConvergenceDetector(config)
