# TradingAgents/research/__init__.py
"""
Deep Research module for comprehensive stock analysis.

Provides multi-provider deep research capabilities with web search grounding.
Priority: Gemini > OpenAI
"""

from .deep_research import (
    DeepResearchAgent,
    DeepResearchTrigger,
    create_deep_research_agent,
)
from .providers.gemini import DeepResearchResult, GEMINI_AVAILABLE
from .providers.openai import OPENAI_AVAILABLE

__all__ = [
    "DeepResearchAgent",
    "DeepResearchTrigger",
    "DeepResearchResult",
    "create_deep_research_agent",
    "GEMINI_AVAILABLE",
    "OPENAI_AVAILABLE",
]
