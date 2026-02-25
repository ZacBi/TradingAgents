# TradingAgents/experts/selector.py
"""Dynamic expert selector based on stock characteristics."""

import logging
import random

from .base import ExpertProfile
from .registry import ExpertRegistry

logger = logging.getLogger(__name__)


# Selection rules mapping stock characteristics to preferred experts
SELECTION_RULES = {
    # (sector, market_cap) -> [preferred_expert_ids]
    ("consumer", "large"): ["buffett", "munger", "lynch"],
    ("finance", "large"): ["buffett", "munger", "graham"],
    ("tech", "large"): ["buffett", "munger", "lynch"],
    ("tech", "mid"): ["lynch", "livermore", "munger"],
    ("tech", "small"): ["lynch", "graham", "livermore"],
    ("healthcare", "large"): ["buffett", "munger", "lynch"],
    ("industrial", "large"): ["buffett", "graham", "munger"],
    ("energy", "large"): ["graham", "buffett", "munger"],
    # High volatility stocks
    ("volatile", "any"): ["livermore", "lynch", "graham"],
    # Deep value / distressed
    ("value", "small"): ["graham", "buffett", "munger"],
    # Default fallback
    ("any", "any"): ["buffett", "munger", "graham"],
}


class ExpertSelector:
    """
    Dynamically selects investment experts based on stock characteristics.

    Selection modes:
    - auto: Automatically select based on stock features
    - manual: Use user-specified expert list
    - random: Random selection (for A/B testing)
    """

    def __init__(self, config: dict):
        """
        Initialize the selector with configuration.

        Args:
            config: Configuration dictionary with keys:
                - max_experts: Maximum number of experts to select (default: 3)
                - expert_selection_mode: "auto", "manual", or "random"
                - selected_experts: List of expert IDs for manual mode
        """
        self.max_experts = config.get("max_experts", 3)
        self.selection_mode = config.get("expert_selection_mode", "auto")
        self.manual_experts = config.get("selected_experts")

    def select(
        self,
        ticker: str,
        stock_info: dict | None = None,
        user_override: list[str] | None = None,
    ) -> list[ExpertProfile]:
        """
        Select experts for analyzing a specific stock.

        Args:
            ticker: Stock ticker symbol
            stock_info: Dictionary containing stock characteristics:
                - sector: Industry sector (e.g., "tech", "consumer")
                - market_cap: Market cap category ("large", "mid", "small")
                - volatility: Volatility level ("high", "medium", "low")
                - style_hint: Investment style hint ("value", "growth")
            user_override: Explicit list of expert IDs to use

        Returns:
            List of selected ExpertProfile objects
        """
        # Priority 1: User override
        if user_override:
            return self._get_experts_by_ids(user_override)

        # Priority 2: Manual mode from config
        if self.selection_mode == "manual" and self.manual_experts:
            return self._get_experts_by_ids(self.manual_experts)

        # Priority 3: Random mode
        if self.selection_mode == "random":
            return self._random_select()

        # Priority 4: Auto mode based on stock characteristics
        return self._auto_select(ticker, stock_info or {})

    def _get_experts_by_ids(self, expert_ids: list[str]) -> list[ExpertProfile]:
        """Get expert profiles by their IDs."""
        experts = []
        for eid in expert_ids[: self.max_experts]:
            profile = ExpertRegistry.get(eid)
            if profile:
                experts.append(profile)
            else:
                logger.warning("Expert '%s' not found in registry.", eid)
        return experts

    def _random_select(self) -> list[ExpertProfile]:
        """Randomly select experts for A/B testing."""
        all_experts = ExpertRegistry.list_all()
        if len(all_experts) <= self.max_experts:
            return all_experts
        return random.sample(all_experts, self.max_experts)

    def _apply_rule_scores(self, scores: dict[str, float], rule_key: tuple, weight: float) -> None:
        """Add scores for experts in SELECTION_RULES[rule_key] (earlier = higher)."""
        for i, eid in enumerate(SELECTION_RULES.get(rule_key, [])):
            scores[eid] = scores.get(eid, 0) + (3 - i) * weight

    def _score_experts_for_stock(
        self, sector: str, market_cap: str, volatility: str, style_hint: str
    ) -> dict[str, float]:
        """Build expert id -> score from sector, market_cap, volatility, style_hint."""
        scores: dict[str, float] = {}
        self._apply_rule_scores(scores, (sector, market_cap), 2.0)
        if volatility == "high":
            self._apply_rule_scores(scores, ("volatile", "any"), 1.5)
        if style_hint == "value":
            for eid in ["graham", "buffett", "munger"]:
                scores[eid] = scores.get(eid, 0) + 1
        elif style_hint == "growth":
            for eid in ["lynch", "livermore"]:
                scores[eid] = scores.get(eid, 0) + 1
        if not scores:
            self._apply_rule_scores(scores, ("any", "any"), 1.0)
        return scores

    def _auto_select(self, ticker: str, stock_info: dict) -> list[ExpertProfile]:
        """
        Automatically select experts based on stock characteristics.

        Uses a scoring system to match experts to stock profiles.
        """
        sector = self._normalize_sector(stock_info.get("sector", "any").lower())
        market_cap = stock_info.get("market_cap", "any").lower()
        volatility = stock_info.get("volatility", "medium").lower()
        style_hint = stock_info.get("style_hint", "").lower()
        scores = self._score_experts_for_stock(sector, market_cap, volatility, style_hint)
        sorted_experts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected_ids = [eid for eid, _ in sorted_experts[: self.max_experts]]
        logger.debug(
            "Auto-selected experts for %s (sector=%s, cap=%s): %s",
            ticker, sector, market_cap, selected_ids,
        )
        return self._get_experts_by_ids(selected_ids)

    def _normalize_sector(self, sector: str) -> str:
        """Normalize sector names to standard categories."""
        sector_map = {
            "technology": "tech",
            "information technology": "tech",
            "software": "tech",
            "consumer discretionary": "consumer",
            "consumer staples": "consumer",
            "consumer cyclical": "consumer",
            "financial services": "finance",
            "financials": "finance",
            "banks": "finance",
            "health care": "healthcare",
            "industrials": "industrial",
            "basic materials": "industrial",
            "utilities": "energy",
            "real estate": "finance",
            "communication services": "tech",
        }
        return sector_map.get(sector, sector)


def create_expert_selector(config: dict) -> ExpertSelector:
    """Factory function to create an ExpertSelector."""
    return ExpertSelector(config)
