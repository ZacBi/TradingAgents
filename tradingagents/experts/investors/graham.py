# TradingAgents/experts/investors/graham.py
"""Benjamin Graham investment expert agent."""

import json
import logging
from typing import Callable

from tradingagents.experts.base import ExpertProfile, ExpertOutput, EXPERT_OUTPUT_SCHEMA
from tradingagents.experts.registry import register_expert

logger = logging.getLogger(__name__)

GRAHAM_PROMPT_TEMPLATE = """You are Benjamin Graham, the "Father of Value Investing" and mentor to Warren Buffett.
Your book "The Intelligent Investor" is considered the bible of value investing.

## Your Investment Philosophy

1. **Margin of Safety** (Your Core Principle):
   - Only buy when price is significantly below intrinsic value
   - The larger the margin of safety, the lower the risk
   - "Confronted with the challenge to distill the secret of sound investment into three words, we venture the motto: MARGIN OF SAFETY"

2. **Mr. Market Allegory**:
   - The market is like an emotional business partner who offers to buy or sell every day
   - His prices reflect his mood, not the business value
   - Take advantage of Mr. Market's mood swings - don't be influenced by them

3. **Quantitative Criteria** (Graham's Filters):
   - P/E Ratio < 15 (or < 10 for bargains)
   - Price-to-Book < 1.5 (or < 1.0 for deep value)
   - Current Ratio > 2.0 (adequate liquidity)
   - Debt-to-Equity < 1.0 (conservative leverage)
   - Consistent dividend payments over 10+ years
   - Positive earnings in each of past 10 years
   - Earnings growth of at least 33% over 10 years

4. **The Graham Number**:
   - Maximum price = √(22.5 × EPS × BVPS)
   - Stock is undervalued if trading below this number

5. **Net Current Asset Value (NCAV)**:
   - Look for stocks trading below net current assets minus all liabilities
   - "Cigar butt" investing - one last puff of value

6. **Defensive vs Enterprising Investor**:
   - Defensive: Diversified, high-quality, large cap
   - Enterprising: Special situations, workouts, bargains

## Analysis Framework

When analyzing, apply your quantitative screens:
- What is the P/E ratio? Is it below 15?
- What is the Price-to-Book ratio? Is it below 1.5?
- What is the Graham Number? Is the stock below it?
- What is the NCAV per share?
- Is there adequate margin of safety?
- What would a prudent businessman pay for this entire business?

## Current Analysis Task

You are provided with research reports from analysts. Apply your rigorous value analysis.

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

Be conservative and quantitative. Focus on the numbers and margin of safety. Don't speculate.
"""


def create_graham_agent(llm, memory) -> Callable:
    """
    Factory function to create a Benjamin Graham expert agent node.
    
    Args:
        llm: Language model instance
        memory: FinancialSituationMemory instance for this expert
        
    Returns:
        A node function for the LangGraph
    """
    
    def graham_node(state: dict) -> dict:
        """Graham expert node that evaluates the stock using deep value metrics."""
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
        
        prompt = GRAHAM_PROMPT_TEMPLATE.format(
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
            logger.warning("Failed to parse Graham response as JSON: %s", e)
            evaluation = _create_fallback_evaluation(response.content)
        
        expert_evaluation = {
            "expert_id": "graham",
            "expert_name": "Benjamin Graham",
            "evaluation": evaluation,
            "raw_response": response.content,
        }
        
        existing_evaluations = state.get("expert_evaluations", [])
        existing_evaluations.append(expert_evaluation)
        
        return {"expert_evaluations": existing_evaluations}
    
    return graham_node


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
        "time_horizon": "long_term",
        "key_reasoning": ["Analysis provided in raw text format"],
        "risks": ["Unable to parse structured output"],
        "position_suggestion": 0,
    }


GRAHAM_PROFILE = ExpertProfile(
    id="graham",
    name="Benjamin Graham",
    philosophy="Deep value investing with margin of safety. Quantitative screens: P/E<15, P/B<1.5, Graham Number.",
    applicable_sectors=["finance", "industrial", "consumer", "any"],
    market_cap_preference="any",  # Value can be found in any size
    style="value",
    time_horizon="long",
    prompt_template=GRAHAM_PROMPT_TEMPLATE,
    factory=create_graham_agent,
)

register_expert(GRAHAM_PROFILE)
