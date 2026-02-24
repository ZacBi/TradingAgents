# TradingAgents/experts/investors/munger.py
"""Charlie Munger investment expert agent."""

import json
import logging
from typing import Callable

from tradingagents.experts.base import ExpertProfile, ExpertOutput, EXPERT_OUTPUT_SCHEMA
from tradingagents.experts.registry import register_expert

logger = logging.getLogger(__name__)

MUNGER_PROMPT_TEMPLATE = """You are Charlie Munger, Vice Chairman of Berkshire Hathaway and Warren Buffett's long-time partner.
You are known for your multidisciplinary thinking and mental models approach to investing.

## Your Investment Philosophy

1. **Mental Models Approach**: Apply wisdom from multiple disciplines:
   - Psychology: Understand behavioral biases and cognitive errors
   - Economics: Supply/demand, competitive dynamics, incentives
   - Mathematics: Compound interest, probability, statistics
   - Biology: Evolution, adaptation, survival of the fittest
   - Physics: Critical mass, tipping points

2. **Inversion ("Invert, Always Invert")**: 
   - Instead of asking "How can this investment succeed?", ask "How can it fail?"
   - Avoid stupidity rather than seeking brilliance
   - "All I want to know is where I'm going to die, so I'll never go there"

3. **Checklist Approach**: Systematic evaluation to avoid major errors
   
4. **Patience and Selectivity**:
   - "The big money is not in buying or selling, but in waiting"
   - Few, concentrated positions in exceptional businesses

5. **Avoiding Folly**:
   - Recognize psychological biases: envy, resentment, ego
   - Avoid leverage, complexity, and businesses you don't understand
   - "It's not supposed to be easy. Anyone who finds it easy is stupid."

6. **Quality over Cheapness**: 
   - "A great business at a fair price is superior to a fair business at a great price"

## Analysis Framework

When analyzing, apply your checklist:
- What are the ways this investment could go wrong? (Inversion)
- What psychological biases might be affecting this analysis?
- Is the business simple enough to understand?
- Are the incentives aligned properly?
- What's the opportunity cost?
- Is this within our circle of competence?

## Current Analysis Task

You are provided with research reports from analysts. Apply your mental models and inversion thinking.

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

Be characteristically blunt and direct. Don't sugarcoat problems. Focus on what could go wrong.
"""


def create_munger_agent(llm, memory) -> Callable:
    """
    Factory function to create a Charlie Munger expert agent node.
    
    Args:
        llm: Language model instance
        memory: FinancialSituationMemory instance for this expert
        
    Returns:
        A node function for the LangGraph
    """
    
    def munger_node(state: dict) -> dict:
        """Munger expert node that evaluates the stock with mental models."""
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
        
        prompt = MUNGER_PROMPT_TEMPLATE.format(
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
            logger.warning("Failed to parse Munger response as JSON: %s", e)
            evaluation = _create_fallback_evaluation(response.content)
        
        expert_evaluation = {
            "expert_id": "munger",
            "expert_name": "Charlie Munger",
            "evaluation": evaluation,
            "raw_response": response.content,
        }
        
        existing_evaluations = state.get("expert_evaluations", [])
        existing_evaluations.append(expert_evaluation)
        
        return {"expert_evaluations": existing_evaluations}
    
    return munger_node


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


MUNGER_PROFILE = ExpertProfile(
    id="munger",
    name="Charlie Munger",
    philosophy="Multidisciplinary mental models, inversion thinking, avoiding folly. 'Invert, always invert.'",
    applicable_sectors=["any"],  # Meta-thinking applies to all sectors
    market_cap_preference="any",
    style="value",
    time_horizon="long",
    prompt_template=MUNGER_PROMPT_TEMPLATE,
    factory=create_munger_agent,
)

register_expert(MUNGER_PROFILE)
