# TradingAgents/prompts/__init__.py
"""Prompt Management module for TradingAgents.

Provides centralized prompt management with Langfuse integration:
- Version control and rollback
- A/B testing capability
- Hot reload (no restart needed)
- Local fallback for reliability

Usage:
    from tradingagents.prompts import PromptManager, PromptNames
    
    pm = PromptManager(config)
    prompt = pm.get_prompt(
        PromptNames.EXPERT_BUFFETT,
        variables={"market_report": report, ...}
    )
"""

from .registry import PromptNames, PROMPT_LABELS, ALL_PROMPT_NAMES
from .manager import (
    PromptManager,
    get_prompt_manager,
    reset_prompt_manager,
)
from .fallback import (
    FALLBACK_TEMPLATES,
    get_fallback_template,
)

__all__ = [
    # Registry
    "PromptNames",
    "PROMPT_LABELS",
    "ALL_PROMPT_NAMES",
    # Manager
    "PromptManager",
    "get_prompt_manager",
    "reset_prompt_manager",
    # Fallback
    "FALLBACK_TEMPLATES",
    "get_fallback_template",
]
