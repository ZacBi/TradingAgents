# TradingAgents/research/providers/gemini.py
"""Gemini Deep Research provider."""

import logging
import os
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not available for deep research")


@dataclass
class DeepResearchResult:
    """Result from a deep research query."""
    report: str
    sources: list[str]
    query: str
    provider: str
    model: str
    tokens_used: int = 0


class GeminiDeepResearchProvider:
    """
    Gemini Deep Research provider using Google's generative AI.
    
    Uses Gemini models with grounding enabled for web search.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Gemini Deep Research provider.
        
        Args:
            model_name: Gemini model to use
            api_key: Google API key (or uses GOOGLE_API_KEY env var)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai is required. "
                "Install with: pip install google-generativeai"
            )
        
        self._model_name = model_name
        
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API key is required for Gemini Deep Research")
        
        genai.configure(api_key=api_key)
        
        # Configure the model with Google Search grounding
        self._model = genai.GenerativeModel(
            model_name=model_name,
            # Enable grounding with Google Search
            tools="google_search_retrieval",
        )
        
        logger.info("Initialized Gemini Deep Research with model=%s", model_name)

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
        # Build the research prompt
        full_query = self._build_research_prompt(query, ticker, context)
        
        try:
            # Generate with grounding
            response = self._model.generate_content(full_query)
            
            # Extract sources from grounding metadata if available
            sources = []
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    if hasattr(grounding, 'web_search_queries'):
                        sources = list(grounding.web_search_queries)
            
            # Get token count
            tokens_used = 0
            if hasattr(response, 'usage_metadata'):
                tokens_used = getattr(response.usage_metadata, 'total_token_count', 0)
            
            return DeepResearchResult(
                report=response.text,
                sources=sources,
                query=query,
                provider="gemini",
                model=self._model_name,
                tokens_used=tokens_used,
            )
            
        except Exception as e:
            logger.error("Gemini Deep Research failed: %s", e)
            return DeepResearchResult(
                report=f"Deep research failed: {str(e)}",
                sources=[],
                query=query,
                provider="gemini",
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
            "You are a professional financial research analyst conducting deep research.",
            "Your task is to provide a comprehensive, well-sourced analysis.",
            "",
            "## Research Query",
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
            "1. Search for the most recent and relevant information",
            "2. Analyze multiple sources for a balanced view",
            "3. Focus on factual, verifiable information",
            "4. Include specific data points, numbers, and dates where available",
            "5. Identify any conflicting information and note the discrepancies",
            "6. Structure your report clearly with sections",
            "",
            "## Output Format",
            "Provide a detailed research report with:",
            "- Executive Summary",
            "- Key Findings",
            "- Detailed Analysis",
            "- Risk Factors",
            "- Conclusion and Outlook",
        ])
        
        return "\n".join(prompt_parts)


def create_gemini_provider(config: dict) -> Optional[GeminiDeepResearchProvider]:
    """
    Factory function to create a Gemini Deep Research provider.
    
    Args:
        config: Configuration with optional keys:
            - deep_research_model: Model name
            - google_api_key: API key
            
    Returns:
        Provider instance or None if not available
    """
    if not GEMINI_AVAILABLE:
        return None
    
    model = config.get("deep_research_model", "gemini-2.0-flash")
    api_key = config.get("google_api_key")
    
    try:
        return GeminiDeepResearchProvider(model_name=model, api_key=api_key)
    except (ImportError, ValueError) as e:
        logger.warning("Failed to create Gemini Deep Research provider: %s", e)
        return None
