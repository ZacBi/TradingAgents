from langchain_core.messages import HumanMessage, RemoveMessage

from tradingagents.agents.utils.core_stock_tools import get_stock_data
from tradingagents.agents.utils.fundamental_data_tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from tradingagents.agents.utils.macro_data_tools import (
    get_cpi_data,
    get_gdp_data,
    get_interest_rate_data,
    get_m2_data,
    get_unemployment_data,
)
from tradingagents.agents.utils.news_data_tools import (
    get_global_news,
    get_insider_transactions,
    get_news,
)
from tradingagents.agents.utils.realtime_data_tools import (
    get_kline_data,
    get_realtime_quote,
)
from tradingagents.agents.utils.technical_indicators_tools import get_indicators
from tradingagents.agents.utils.valuation_data_tools import (
    get_earnings_dates,
    get_institutional_holders,
    get_valuation_metrics,
)


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


