from tradingagents.agents.base import BaseAnalyst
from tradingagents.agents.utils.news_data_tools import get_global_news, get_news
from tradingagents.prompts import PromptNames


class NewsAnalyst(BaseAnalyst):
    """News Analyst agent using BaseAnalyst."""
    
    def __init__(self, llm):
        """Initialize News Analyst.
        
        Args:
            llm: Language model instance
        """
        tools = [get_news, get_global_news]
        super().__init__(
            llm=llm,
            tools=tools,
            prompt_name=PromptNames.ANALYST_NEWS,
            report_field="news_report",
            name="News Analyst",
        )


def create_news_analyst(llm):
    """Factory function to create News Analyst.
    
    Args:
        llm: Language model instance
        
    Returns:
        News analyst node function
    """
    analyst = NewsAnalyst(llm)
    return analyst.execute
