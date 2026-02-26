
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.core_stock_tools import get_stock_data
from tradingagents.agents.utils.technical_indicators_tools import get_indicators
from tradingagents.prompts import PromptNames, get_prompt_manager


def create_market_analyst(llm):
    pm = get_prompt_manager()

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        state["company_of_interest"]

        tools = [
            get_stock_data,
            get_indicators,
        ]

        parts = pm.get_prompt_parts(PromptNames.ANALYST_MARKET)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    parts["system_template"],
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=parts["template"])
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
