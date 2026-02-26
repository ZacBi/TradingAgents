from tradingagents.agents.base import BaseAnalyst
from tradingagents.agents.utils.fundamental_data_tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from tradingagents.prompts import PromptNames


class FundamentalsAnalyst(BaseAnalyst):
    """Fundamentals Analyst agent using BaseAnalyst."""
    
    def __init__(self, llm):
        """Initialize Fundamentals Analyst.
        
        Args:
            llm: Language model instance
        """
        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]
        super().__init__(
            llm=llm,
            tools=tools,
            prompt_name=PromptNames.ANALYST_FUNDAMENTALS,
            report_field="fundamentals_report",
            name="Fundamentals Analyst",
        )


def create_fundamentals_analyst(llm):
    """Factory function to create Fundamentals Analyst.
    
    Args:
        llm: Language model instance
        
    Returns:
        Fundamentals analyst node function
    """
    analyst = FundamentalsAnalyst(llm)
    return analyst.execute
