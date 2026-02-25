import functools

from tradingagents.prompts import PromptNames, get_prompt_manager


def create_trader(llm, memory):
    pm = get_prompt_manager()

    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for _i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        parts = pm.get_prompt_parts(PromptNames.TRADER_MAIN, variables={
            "past_memory_str": past_memory_str,
            "company_name": company_name,
            "investment_plan": investment_plan,
        })

        messages = [
            {"role": "system", "content": parts["system_template"]},
            {"role": "user", "content": parts["user_template"]},
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
