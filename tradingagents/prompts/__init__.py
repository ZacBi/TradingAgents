# TradingAgents/prompts/__init__.py
"""Prompt Management module for TradingAgents.

Provides centralized prompt management with Langfuse integration:
- Version control and rollback
- A/B testing capability
- Hot reload (no restart needed)
- Local fallback for reliability (YAML-based)

Usage:
    from tradingagents.prompts import PromptManager, PromptNames
    
    pm = PromptManager(config)
    prompt = pm.get_prompt(
        PromptNames.EXPERT_BUFFETT,
        variables={"market_report": report, ...}
    )
"""

from .registry import PromptNames, PROMPT_LABELS, ALL_PROMPT_NAMES, TEMPLATE_PATH_MAP
from .manager import (
    PromptManager,
    get_prompt_manager,
    reset_prompt_manager,
)

__all__ = [
    # Registry
    "PromptNames",
    "PROMPT_LABELS",
    "ALL_PROMPT_NAMES",
    "TEMPLATE_PATH_MAP",
    # Manager
    "PromptManager",
    "get_prompt_manager",
    "reset_prompt_manager",
]
