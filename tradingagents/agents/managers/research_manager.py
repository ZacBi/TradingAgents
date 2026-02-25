import logging

from tradingagents.prompts import PromptNames, get_prompt_manager

logger = logging.getLogger(__name__)


def create_research_manager(llm, memory):
    pm = get_prompt_manager()

    def research_manager_node(state) -> dict:
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for _i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = pm.get_prompt(PromptNames.MANAGER_RESEARCH, variables={
            "history": history,
            "past_memory_str": past_memory_str,
        })
        try:
            response = llm.invoke(prompt)
            content = response.content
        except Exception as e:
            logger.exception("Research Manager LLM invoke failed")
            content = f"Error during research synthesis; defaulting to HOLD. Reason: {e}"

        new_investment_debate_state = {
            "judge_decision": content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": content,
        }

    return research_manager_node
