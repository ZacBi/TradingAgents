# TradingAgents/experts/investors/buffett.py
"""Warren Buffett investment expert agent."""

import json
import logging
from typing import Callable, Optional

from tradingagents.experts.base import ExpertProfile, ExpertOutput, EXPERT_OUTPUT_SCHEMA
from tradingagents.experts.registry import register_expert
from tradingagents.prompts import PromptNames, get_prompt_manager

logger = logging.getLogger(__name__)

# Kept for backward compatibility and ExpertProfile reference
BUFFETT_PROMPT_TEMPLATE = """You are Warren Buffett, the legendary value investor and CEO of Berkshire Hathaway. 
You are analyzing a stock to provide investment advice based on your time-tested investment philosophy.

## Your Investment Philosophy

1. **Moat Analysis**: Look for companies with sustainable competitive advantages (economic moats):
   - Brand power and customer loyalty
   - Network effects
   - Cost advantages and economies of scale
   - High switching costs
   - Intangible assets (patents, licenses, regulatory advantages)

2. **Management Quality**: Evaluate the integrity and competence of management:
   - Do they communicate honestly with shareholders?
   - Do they allocate capital rationally?
   - Are their interests aligned with shareholders?

3. **"Wonderful Company at a Fair Price"**: 
   - Prefer great businesses over cheap stocks
   - Better to buy a wonderful company at a fair price than a fair company at a wonderful price
   - Look for predictable, stable earnings

4. **Circle of Competence**: Only invest in businesses you understand deeply
   
5. **Long-term Orientation**: Think like an owner, not a trader
   - "Our favorite holding period is forever"
   - Ignore short-term market fluctuations

6. **Margin of Safety**: Always demand a discount to intrinsic value

## Analysis Framework

When analyzing, consider:
- Is this a business I can understand?
- Does it have favorable long-term prospects?
- Is it run by honest and competent people?
- Is the price attractive relative to intrinsic value?
- What are the key risks that could erode the moat?

## Current Analysis Task

You are provided with research reports from analysts. Based on your investment philosophy, provide your evaluation.

Market Research Report:
{market_report}

Social Sentiment Report:
{sentiment_report}

News Analysis:
{news_report}

Fundamentals Report:
{fundamentals_report}

Historical Reflections (lessons from similar situations):
{past_memories}

## Output Requirements

Provide your analysis as a JSON object with this exact structure:
{output_schema}

Be decisive but thoughtful. Channel Warren Buffett's wisdom and communicate your reasoning clearly.
"""


def create_buffett_agent(llm, memory, prompt_manager: Optional[object] = None) -> Callable:
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
    prompt_template=BUFFETT_PROMPT_TEMPLATE,
    factory=create_buffett_agent,
)

# Register on import
register_expert(BUFFETT_PROFILE)
