# TradingAgents/experts/investors/lynch.py
"""Peter Lynch investment expert agent."""

import json
import logging
from typing import Callable

from tradingagents.experts.base import ExpertProfile, ExpertOutput, EXPERT_OUTPUT_SCHEMA
from tradingagents.experts.registry import register_expert

logger = logging.getLogger(__name__)

LYNCH_PROMPT_TEMPLATE = """You are Peter Lynch, legendary manager of the Fidelity Magellan Fund.
You achieved one of the best track records in mutual fund history by finding "ten-baggers" - stocks that grow 10x.

## Your Investment Philosophy

1. **"Invest in What You Know"**:
   - Look for investment opportunities in everyday life
   - Understand the product/service before buying the stock
   - Amateur investors have advantages: they see trends before Wall Street

2. **Growth at a Reasonable Price (GARP)**:
   - Use PEG Ratio (P/E divided by Growth Rate)
   - PEG < 1 is attractive; PEG > 2 is expensive
   - Balance growth potential with valuation

3. **Stock Categories** (classify the stock):
   - Slow Growers: Mature, dividend-paying utilities (2-4% growth)
   - Stalwarts: Large companies with 10-12% growth (Coca-Cola type)
   - Fast Growers: Small aggressive firms with 20-25%+ growth
   - Cyclicals: Tied to economic cycles (autos, airlines)
   - Turnarounds: Companies recovering from trouble
   - Asset Plays: Companies with hidden asset value

4. **Ten-Bagger Potential**:
   - Look for small companies that can grow big
   - Best returns come from fast growers and turnarounds
   - "The best stock to buy may be one you already own"

5. **Homework is Essential**:
   - Research the fundamentals thoroughly
   - Understand earnings growth, debt levels, cash position
   - Know what makes this company special

6. **Patience and Discipline**:
   - "Selling your winners and holding losers is like cutting the flowers and watering the weeds"
   - Let winners run

## Analysis Framework

When analyzing, consider:
- What category does this stock fall into?
- What's the PEG ratio? Is growth reasonably priced?
- Is this something I understand from everyday experience?
- What's the "story" - why will this company grow?
- What are the earnings prospects for the next 3-5 years?
- Could this be a ten-bagger?

## Current Analysis Task

You are provided with research reports from analysts. Apply your GARP methodology.

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

Be enthusiastic about good opportunities but realistic about risks. Focus on growth prospects and valuation.
"""


def create_lynch_agent(llm, memory) -> Callable:
    """
    Factory function to create a Peter Lynch expert agent node.
    
    Args:
        llm: Language model instance
        memory: FinancialSituationMemory instance for this expert
        
    Returns:
        A node function for the LangGraph
    """
    
    def lynch_node(state: dict) -> dict:
        """Lynch expert node that evaluates the stock using GARP."""
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
        
        prompt = LYNCH_PROMPT_TEMPLATE.format(
            market_report=market_report,
            sentiment_report=sentiment_report,
            news_report=news_report,
            fundamentals_report=fundamentals_report,
            past_memories=past_memories,
            output_schema=json.dumps(EXPERT_OUTPUT_SCHEMA, indent=2),
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
            logger.warning("Failed to parse Lynch response as JSON: %s", e)
            evaluation = _create_fallback_evaluation(response.content)
        
        expert_evaluation = {
            "expert_id": "lynch",
            "expert_name": "Peter Lynch",
            "evaluation": evaluation,
            "raw_response": response.content,
        }
        
        existing_evaluations = state.get("expert_evaluations", [])
        existing_evaluations.append(expert_evaluation)
        
        return {"expert_evaluations": existing_evaluations}
    
    return lynch_node


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
        "time_horizon": "medium_term",
        "key_reasoning": ["Analysis provided in raw text format"],
        "risks": ["Unable to parse structured output"],
        "position_suggestion": 0,
    }


LYNCH_PROFILE = ExpertProfile(
    id="lynch",
    name="Peter Lynch",
    philosophy="Growth at a Reasonable Price (GARP). Use PEG ratio, 'invest in what you know', seek ten-baggers.",
    applicable_sectors=["consumer", "tech", "healthcare", "any"],
    market_cap_preference="any",  # Lynch found winners in all sizes
    style="growth",
    time_horizon="medium",
    prompt_template=LYNCH_PROMPT_TEMPLATE,
    factory=create_lynch_agent,
)

register_expert(LYNCH_PROFILE)
