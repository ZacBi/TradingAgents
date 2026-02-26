
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.news_data_tools import get_news
from tradingagents.prompts import PromptNames, get_prompt_manager


def create_social_media_analyst(llm):
    pm = get_prompt_manager()

    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        state["company_of_interest"]

        tools = [
            get_news,
        ]

        parts = pm.get_prompt_parts(PromptNames.ANALYST_SOCIAL)

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
            "sentiment_report": report,
        }

    return social_media_analyst_node
