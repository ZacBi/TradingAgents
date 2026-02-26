from tradingagents.agents.base import BaseAnalyst
from tradingagents.agents.utils.news_data_tools import get_news
from tradingagents.prompts import PromptNames


class SocialMediaAnalyst(BaseAnalyst):
    """Social Media Analyst agent using BaseAnalyst."""
    
    def __init__(self, llm):
        """Initialize Social Media Analyst.
        
        Args:
            llm: Language model instance
        """
        tools = [get_news]
        super().__init__(
            llm=llm,
            tools=tools,
            prompt_name=PromptNames.ANALYST_SOCIAL,
            report_field="sentiment_report",
            name="Social Media Analyst",
        )


def create_social_media_analyst(llm):
    """Factory function to create Social Media Analyst.
    
    Args:
        llm: Language model instance
        
    Returns:
        Social media analyst node function
    """
    analyst = SocialMediaAnalyst(llm)
    return analyst.execute
