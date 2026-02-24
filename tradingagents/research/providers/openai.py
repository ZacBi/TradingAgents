# TradingAgents/research/providers/openai.py
"""OpenAI Deep Research provider."""

import logging
import os
from typing import Optional

from .gemini import DeepResearchResult

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai not available for deep research")


class OpenAIDeepResearchProvider:
    """
    OpenAI Deep Research provider.
    
    Uses GPT-4 with web search tools (via Responses API when available)
    or standard chat completions with search prompt.
    """

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the OpenAI Deep Research provider.
        
        Args:
            model_name: OpenAI model to use
            api_key: OpenAI API key (or uses OPENAI_API_KEY env var)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai is required. Install with: pip install openai"
            )
        
        self._model_name = model_name
        
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self._client = OpenAI(api_key=api_key)
        
        logger.info("Initialized OpenAI Deep Research with model=%s", model_name)

    def research(
        self,
        query: str,
        ticker: Optional[str] = None,
        context: Optional[str] = None,
    ) -> DeepResearchResult:
        """
        Perform deep research on a query.
        
        Args:
            query: Research query
            ticker: Optional stock ticker for context
            context: Optional additional context
            
        Returns:
            DeepResearchResult with report and sources
        """
        full_prompt = self._build_research_prompt(query, ticker, context)
        
        try:
            # Use chat completions
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional financial research analyst. "
                            "Provide comprehensive, well-structured research reports "
                            "based on your knowledge. Be specific with data and dates."
                        )
                    },
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            
            report = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            return DeepResearchResult(
                report=report,
                sources=[],  # No web search in standard completions
                query=query,
                provider="openai",
                model=self._model_name,
                tokens_used=tokens_used,
            )
            
        except Exception as e:
            logger.error("OpenAI Deep Research failed: %s", e)
            return DeepResearchResult(
                report=f"Deep research failed: {str(e)}",
                sources=[],
                query=query,
                provider="openai",
                model=self._model_name,
            )

    def _build_research_prompt(
        self,
        query: str,
        ticker: Optional[str],
        context: Optional[str],
    ) -> str:
        """Build a comprehensive research prompt."""
        prompt_parts = [
            "## Research Request",
            query,
        ]
        
        if ticker:
            prompt_parts.extend([
                "",
                f"## Stock of Interest: {ticker}",
            ])
        
        if context:
            prompt_parts.extend([
                "",
                "## Additional Context",
                context,
            ])
        
        prompt_parts.extend([
            "",
            "## Instructions",
            "Provide a detailed research report covering:",
            "1. Executive Summary - Key takeaways in 2-3 sentences",
            "2. Key Findings - Bulleted list of main discoveries",
            "3. Detailed Analysis - In-depth examination of the topic",
            "4. Risk Factors - Potential concerns and red flags",
            "5. Conclusion - Final assessment and outlook",
            "",
            "Be specific with numbers, dates, and data points where possible.",
        ])
        
        return "\n".join(prompt_parts)


def create_openai_provider(config: dict) -> Optional[OpenAIDeepResearchProvider]:
    """
    Factory function to create an OpenAI Deep Research provider.
    
    Args:
        config: Configuration with optional keys:
            - deep_research_model: Model name
            - openai_api_key: API key
            
    Returns:
        Provider instance or None if not available
    """
    if not OPENAI_AVAILABLE:
        return None
    
    model = config.get("deep_research_model", "gpt-4o")
    api_key = config.get("openai_api_key")
    
    try:
        return OpenAIDeepResearchProvider(model_name=model, api_key=api_key)
    except (ImportError, ValueError) as e:
        logger.warning("Failed to create OpenAI Deep Research provider: %s", e)
        return None
