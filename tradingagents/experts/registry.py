# TradingAgents/experts/registry.py
"""Expert registry for managing and discovering investment experts."""

import logging

from .base import ExpertProfile

logger = logging.getLogger(__name__)


class ExpertRegistry:
    """
    Global registry for investment expert agents.

    Provides registration, discovery, and filtering of experts.
    Experts register themselves at module import time.
    """

    _experts: dict[str, ExpertProfile] = {}

    @classmethod
    def register(cls, profile: ExpertProfile) -> None:
        """
        Register an expert to the global registry.

        Args:
            profile: The expert profile to register

        Raises:
            ValueError: If an expert with the same ID already exists
        """
        if profile.id in cls._experts:
            logger.warning(
                "Expert '%s' already registered, overwriting.", profile.id
            )
        cls._experts[profile.id] = profile
        logger.debug("Registered expert: %s (%s)", profile.id, profile.name)

    @classmethod
    def unregister(cls, expert_id: str) -> bool:
        """
        Remove an expert from the registry.

        Args:
            expert_id: The ID of the expert to remove

        Returns:
            True if expert was removed, False if not found
        """
        if expert_id in cls._experts:
            del cls._experts[expert_id]
            return True
        return False

    @classmethod
    def get(cls, expert_id: str) -> ExpertProfile | None:
        """
        Get a specific expert by ID.

        Args:
            expert_id: The unique identifier of the expert

        Returns:
            The expert profile if found, None otherwise
        """
        return cls._experts.get(expert_id)

    @classmethod
    def get_or_raise(cls, expert_id: str) -> ExpertProfile:
        """
        Get a specific expert by ID, raising if not found.

        Args:
            expert_id: The unique identifier of the expert

        Returns:
            The expert profile

        Raises:
            KeyError: If expert not found
        """
        profile = cls._experts.get(expert_id)
        if profile is None:
            available = list(cls._experts.keys())
            raise KeyError(
                f"Expert '{expert_id}' not found. Available: {available}"
            )
        return profile

    @classmethod
    def list_all(cls) -> list[ExpertProfile]:
        """
        List all registered experts.

        Returns:
            List of all registered expert profiles
        """
        return list(cls._experts.values())

    @classmethod
    def list_ids(cls) -> list[str]:
        """
        List all registered expert IDs.

        Returns:
            List of expert IDs
        """
        return list(cls._experts.keys())

    @classmethod
    def filter_by(
        cls,
        sector: str | None = None,
        style: str | None = None,
        market_cap: str | None = None,
        time_horizon: str | None = None,
    ) -> list[ExpertProfile]:
        """
        Filter experts by various criteria.

        Args:
            sector: Filter by applicable sector (e.g., "tech", "consumer")
            style: Filter by investment style (e.g., "value", "growth")
            market_cap: Filter by market cap preference (e.g., "large", "small")
            time_horizon: Filter by time horizon (e.g., "short", "long")

        Returns:
            List of expert profiles matching all specified criteria
        """
        results = []
        for profile in cls._experts.values():
            # Check sector match
            if sector:
                if "any" not in profile.applicable_sectors and sector not in profile.applicable_sectors:
                    continue

            # Check style match
            if style and profile.style != style and profile.style != "hybrid":
                continue

            # Check market cap match
            if market_cap and profile.market_cap_preference != "any" and profile.market_cap_preference != market_cap:
                continue

            # Check time horizon match
            if time_horizon and profile.time_horizon != time_horizon:
                continue

            results.append(profile)

        return results

    @classmethod
    def clear(cls) -> None:
        """Clear all registered experts. Mainly for testing."""
        cls._experts.clear()

    @classmethod
    def count(cls) -> int:
        """Return the number of registered experts."""
        return len(cls._experts)


def register_expert(profile: ExpertProfile) -> ExpertProfile:
    """
    Decorator-style function to register an expert.

    Can be used as:
        profile = register_expert(ExpertProfile(...))

    Args:
        profile: The expert profile to register

    Returns:
        The same profile (for chaining)
    """
    ExpertRegistry.register(profile)
    return profile
