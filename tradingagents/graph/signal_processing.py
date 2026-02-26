# TradingAgents/graph/signal_processing.py

import logging

from langchain_openai import ChatOpenAI

from tradingagents.prompts import PromptNames, get_prompt_manager

logger = logging.getLogger(__name__)


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize with an LLM for processing."""
        self.quick_thinking_llm = quick_thinking_llm
        self.pm = get_prompt_manager()

    def process_signal(self, full_signal: str) -> str:
        """
        Process a full trading signal to extract the core decision.

        Args:
            full_signal: Complete trading signal text

        Returns:
            Extracted decision (BUY, SELL, or HOLD)
        """
        system_prompt = self.pm.get_prompt(PromptNames.GRAPH_SIGNAL_EXTRACTION)
        messages = [
            ("system", system_prompt),
            ("human", full_signal),
        ]
        try:
            return self.quick_thinking_llm.invoke(messages).content
        except Exception:
            logger.exception("SignalProcessor LLM invoke failed")
            return "HOLD"
