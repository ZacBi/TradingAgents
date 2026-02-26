from tradingagents.agents.base import BaseAnalyst
from tradingagents.agents.utils.core_stock_tools import get_stock_data
from tradingagents.agents.utils.technical_indicators_tools import get_indicators
from tradingagents.prompts import PromptNames


class MarketAnalyst(BaseAnalyst):
    """Market Analyst agent using BaseAnalyst."""
    
    def __init__(self, llm):
        """Initialize Market Analyst.
        
        Args:
            llm: Language model instance
        """
        tools = [get_stock_data, get_indicators]
        super().__init__(
            llm=llm,
            tools=tools,
            prompt_name=PromptNames.ANALYST_MARKET,
            report_field="market_report",
            name="Market Analyst",
        )


def create_market_analyst(llm):
    """Factory function to create Market Analyst.
    
    Args:
        llm: Language model instance
        
    Returns:
        Market analyst node function
    """
    analyst = MarketAnalyst(llm)
    return analyst.execute
