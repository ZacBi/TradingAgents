# TradingAgents/experts/investors/buffett.py
"""Warren Buffett investment expert agent."""

import json
import logging
from collections.abc import Callable

from tradingagents.experts.base import EXPERT_OUTPUT_SCHEMA, ExpertOutput, ExpertProfile
from tradingagents.experts.registry import register_expert
from tradingagents.prompts import PromptNames, get_prompt_manager

logger = logging.getLogger(__name__)


def create_buffett_agent(llm, memory, prompt_manager: object | None = None) -> Callable:
    """
    Factory function to create a Warren Buffett expert agent node.

    Args:
        llm: Language model instance
        memory: FinancialSituationMemory instance for this expert
        prompt_manager: Optional PromptManager instance for centralized prompts

    Returns:
        A node function for the LangGraph
    """
    # Use provided prompt_manager or get global instance
    pm = prompt_manager or get_prompt_manager()

    def buffett_node(state: dict) -> dict:
        """Buffett expert node that evaluates the stock."""
        # Extract analyst reports from state
        market_report = state.get("market_report", "Not available")
        sentiment_report = state.get("sentiment_report", "Not available")
        news_report = state.get("news_report", "Not available")
        fundamentals_report = state.get("fundamentals_report", "Not available")

        # Build context for memory retrieval
        curr_situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"

        # Retrieve past memories
        past_memories = ""
        if memory:
            memories = memory.get_memories(curr_situation, n_matches=2)
            for rec in memories:
                past_memories += rec.get("recommendation", "") + "\n\n"

        if not past_memories:
            past_memories = "No relevant historical analysis available."

        # Build prompt using PromptManager
        prompt = pm.get_prompt(
            PromptNames.EXPERT_BUFFETT,
            variables={
                "market_report": market_report,
                "sentiment_report": sentiment_report,
                "news_report": news_report,
                "fundamentals_report": fundamentals_report,
                "past_memories": past_memories,
                "output_schema": json.dumps(EXPERT_OUTPUT_SCHEMA, indent=2),
            }
        )

        # Get LLM response
        response = llm.invoke(prompt)

        # Parse response
        try:
            # Try to extract JSON from response
            content = response.content
            # Find JSON in response
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                evaluation = json.loads(json_str)
            else:
                # Fallback if no JSON found
                evaluation = _create_fallback_evaluation(content)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse Buffett response as JSON: %s", e)
            evaluation = _create_fallback_evaluation(response.content)

        # Build expert evaluation entry
        expert_evaluation = {
            "expert_id": "buffett",
            "expert_name": "Warren Buffett",
            "evaluation": evaluation,
            "raw_response": response.content,
        }

        # Update state with expert evaluation
        existing_evaluations = state.get("expert_evaluations", [])
        existing_evaluations.append(expert_evaluation)

        return {"expert_evaluations": existing_evaluations}

    return buffett_node


def _create_fallback_evaluation(content: str) -> ExpertOutput:
    """Create a fallback evaluation when JSON parsing fails."""
    # Try to infer recommendation from content
    content_lower = content.lower()
    if "buy" in content_lower and "not buy" not in content_lower:
        recommendation = "BUY"
    elif "sell" in content_lower:
        recommendation = "SELL"
    else:
        recommendation = "HOLD"

    return {
        "recommendation": recommendation,
        "confidence": 0.5,
        "time_horizon": "long_term",
        "key_reasoning": ["Analysis provided in raw text format"],
        "risks": ["Unable to parse structured output"],
        "position_suggestion": 0,
    }


# Create and register the profile
BUFFETT_PROFILE = ExpertProfile(
    id="buffett",
    name="Warren Buffett",
    philosophy="Value investing with focus on economic moats, management quality, and long-term ownership. 'Wonderful company at a fair price.'",
    applicable_sectors=["consumer", "finance", "industrial", "any"],
    market_cap_preference="large",
    style="value",
    time_horizon="long",
    prompt_template="",
    factory=create_buffett_agent,
)

# Register on import
register_expert(BUFFETT_PROFILE)
