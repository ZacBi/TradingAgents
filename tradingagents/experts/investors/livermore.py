# TradingAgents/experts/investors/livermore.py
"""Jesse Livermore trading expert agent."""

import json
import logging
from typing import Callable, Optional

from tradingagents.experts.base import ExpertProfile, ExpertOutput, EXPERT_OUTPUT_SCHEMA
from tradingagents.experts.registry import register_expert
from tradingagents.prompts import PromptNames, get_prompt_manager

logger = logging.getLogger(__name__)


def create_livermore_agent(llm, memory, prompt_manager: Optional[object] = None) -> Callable:
    """
    Factory function to create a Jesse Livermore expert agent node.
    
    Args:
        llm: Language model instance
        memory: FinancialSituationMemory instance for this expert
        prompt_manager: Optional PromptManager instance for centralized prompts
        
    Returns:
        A node function for the LangGraph
    """
    pm = prompt_manager or get_prompt_manager()
    
    def livermore_node(state: dict) -> dict:
        """Livermore expert node that evaluates the stock from a trading perspective."""
        market_report = state.get("market_report", "Not available")
        sentiment_report = state.get("sentiment_report", "Not available")
        news_report = state.get("news_report", "Not available")
        fundamentals_report = state.get("fundamentals_report", "Not available")
        
        curr_situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        
        past_memories = ""
        if memory:
            memories = memory.get_memories(curr_situation, n_matches=2)
            for rec in memories:
                past_memories += rec.get("recommendation", "") + "\n\n"
        
        if not past_memories:
            past_memories = "No relevant historical analysis available."
        
        prompt = pm.get_prompt(
            PromptNames.EXPERT_LIVERMORE,
            variables={
                "market_report": market_report,
                "sentiment_report": sentiment_report,
                "news_report": news_report,
                "fundamentals_report": fundamentals_report,
                "past_memories": past_memories,
                "output_schema": json.dumps(EXPERT_OUTPUT_SCHEMA, indent=2),
            }
        )
        
        response = llm.invoke(prompt)
        
        try:
            content = response.content
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                evaluation = json.loads(json_str)
            else:
                evaluation = _create_fallback_evaluation(content)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse Livermore response as JSON: %s", e)
            evaluation = _create_fallback_evaluation(response.content)
        
        expert_evaluation = {
            "expert_id": "livermore",
            "expert_name": "Jesse Livermore",
            "evaluation": evaluation,
            "raw_response": response.content,
        }
        
        existing_evaluations = state.get("expert_evaluations", [])
        existing_evaluations.append(expert_evaluation)
        
        return {"expert_evaluations": existing_evaluations}
    
    return livermore_node


def _create_fallback_evaluation(content: str) -> ExpertOutput:
    """Create a fallback evaluation when JSON parsing fails."""
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
        "time_horizon": "short_term",
        "key_reasoning": ["Analysis provided in raw text format"],
        "risks": ["Unable to parse structured output"],
        "position_suggestion": 0,
    }


LIVERMORE_PROFILE = ExpertProfile(
    id="livermore",
    name="Jesse Livermore",
    philosophy="Trend following, pivotal points, market timing, strict risk management. 'The trend is your friend.'",
    applicable_sectors=["any"],  # Trading style applies to any liquid stock
    market_cap_preference="any",
    style="momentum",
    time_horizon="short",
    prompt_template="",
    factory=create_livermore_agent,
)

register_expert(LIVERMORE_PROFILE)
