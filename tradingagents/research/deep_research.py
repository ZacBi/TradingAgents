# TradingAgents/research/deep_research.py
"""Deep Research Agent for comprehensive stock analysis."""

import logging
from collections.abc import Callable

from .providers.gemini import (
    GEMINI_AVAILABLE,
    DeepResearchResult,
    create_gemini_provider,
)
from .providers.openai import (
    OPENAI_AVAILABLE,
    create_openai_provider,
)

logger = logging.getLogger(__name__)


class DeepResearchTrigger:
    """Determines when to trigger deep research."""

    @staticmethod
    def should_trigger(state: dict, config: dict) -> bool:
        """
        Determine if deep research should be triggered.

        Args:
            state: Current agent state
            config: Configuration dictionary

        Returns:
            True if deep research should run
        """
        # Check if deep research is enabled
        if not config.get("deep_research_enabled", False):
            return False

        # Check force trigger
        if config.get("force_deep_research", False):
            return True

        triggers = config.get("deep_research_triggers", [])

        # Check each trigger condition
        for trigger in triggers:
            if trigger == "first_analysis":
                # Check if this is first analysis of this stock
                # (no memory entries for this ticker)
                # This would need memory integration
                pass

            elif trigger == "pre_earnings":
                # Check if earnings are within lookahead window
                # This requires earnings_dates data
                pass

            elif trigger == "high_volatility":
                # Check if recent volatility exceeds threshold
                pass

        return False


class DeepResearchAgent:
    """
    Deep Research Agent that performs comprehensive web-based research.

    Supports multiple providers with Gemini as priority.
    """

    def __init__(self, config: dict):
        """
        Initialize the Deep Research Agent.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self._provider = None

        provider_name = config.get("deep_research_provider", "gemini")

        # Try Gemini first (priority)
        if provider_name == "gemini" or (provider_name != "openai" and GEMINI_AVAILABLE):
            self._provider = create_gemini_provider(config)
            if self._provider:
                logger.info("Using Gemini for Deep Research")

        # Fallback to OpenAI
        if self._provider is None and OPENAI_AVAILABLE:
            self._provider = create_openai_provider(config)
            if self._provider:
                logger.info("Using OpenAI for Deep Research")

        if self._provider is None:
            logger.warning("No Deep Research provider available")

    def research(
        self,
        query: str,
        ticker: str | None = None,
        analyst_reports: dict | None = None,
    ) -> DeepResearchResult:
        """
        Perform deep research.

        Args:
            query: Research query
            ticker: Optional stock ticker
            analyst_reports: Optional dict with analyst reports for context

        Returns:
            DeepResearchResult
        """
        if self._provider is None:
            return DeepResearchResult(
                report="Deep Research not available (no provider configured)",
                sources=[],
                query=query,
                provider="none",
                model="none",
            )

        # Build context from analyst reports
        context = None
        if analyst_reports:
            context_parts = []
            for report_name, report_content in analyst_reports.items():
                if report_content:
                    context_parts.append(f"### {report_name}\n{report_content[:1000]}...")
            if context_parts:
                context = "\n\n".join(context_parts)

        return self._provider.research(query, ticker, context)

    @property
    def available(self) -> bool:
        """Check if deep research is available."""
        return self._provider is not None


def create_deep_research_agent(llm, config: dict) -> Callable:
    """
    Factory function to create a Deep Research agent node.

    Args:
        llm: Language model (not used directly, provider has own model)
        config: Configuration dictionary

    Returns:
        A node function for the LangGraph
    """
    agent = DeepResearchAgent(config)

    def deep_research_node(state: dict) -> dict:
        """Deep Research node that performs comprehensive research."""
        # Check if we should trigger
        if not DeepResearchTrigger.should_trigger(state, config):
            return {}

        ticker = state.get("company_of_interest")

        # Build research query
        query = f"Comprehensive investment research for {ticker}"
        if ticker:
            query += f" ({ticker})"
        query += ". Include recent news, financial performance, competitive landscape, and key risks."

        # Gather analyst reports for context
        analyst_reports = {
            "Market Analysis": state.get("market_report"),
            "Sentiment Analysis": state.get("sentiment_report"),
            "News Analysis": state.get("news_report"),
            "Fundamentals": state.get("fundamentals_report"),
        }

        # Perform research
        result = agent.research(query, ticker, analyst_reports)

        logger.info(
            "Deep Research completed: provider=%s, tokens=%d",
            result.provider, result.tokens_used
        )

        return {
            "deep_research_report": result.report,
            "deep_research_sources": result.sources,
        }

    return deep_research_node
