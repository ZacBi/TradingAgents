# TradingAgents/experts/__init__.py
"""
Extensible Expert Framework for TradingAgents.

This module provides a plugin-style registration system for investment experts.
Experts auto-register themselves when imported.

Usage:
    from tradingagents.experts import ExpertRegistry, ExpertSelector

    # List all registered experts
    experts = ExpertRegistry.list_all()

    # Get a specific expert
    buffett = ExpertRegistry.get("buffett")

    # Select experts automatically for a stock
    selector = ExpertSelector(config)
    selected = selector.select("AAPL", {"sector": "tech", "market_cap": "large"})
"""

# Import investors to trigger auto-registration
from . import investors
from .base import EXPERT_OUTPUT_SCHEMA, ExpertOutput, ExpertProfile
from .investors import (
    BUFFETT_PROFILE,
    GRAHAM_PROFILE,
    LIVERMORE_PROFILE,
    LYNCH_PROFILE,
    MUNGER_PROFILE,
    create_buffett_agent,
    create_graham_agent,
    create_livermore_agent,
    create_lynch_agent,
    create_munger_agent,
)
from .registry import ExpertRegistry, register_expert
from .selector import ExpertSelector, create_expert_selector
from .team import create_expert_team_node

__all__ = [
    # Base types
    "ExpertProfile",
    "ExpertOutput",
    "EXPERT_OUTPUT_SCHEMA",
    # Side-effect import for auto-registration
    "investors",
    # Registry
    "ExpertRegistry",
    "register_expert",
    # Selector
    "ExpertSelector",
    "create_expert_selector",
    # Expert profiles
    "BUFFETT_PROFILE",
    "MUNGER_PROFILE",
    "LYNCH_PROFILE",
    "LIVERMORE_PROFILE",
    "GRAHAM_PROFILE",
    # Factory functions
    "create_buffett_agent",
    "create_munger_agent",
    "create_lynch_agent",
    "create_livermore_agent",
    "create_graham_agent",
    "create_expert_team_node",
]
