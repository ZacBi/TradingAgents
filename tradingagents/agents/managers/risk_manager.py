import logging

from tradingagents.prompts import PromptNames, get_prompt_manager

logger = logging.getLogger(__name__)


def create_risk_manager(llm, memory):
    pm = get_prompt_manager()

    def risk_manager_node(state) -> dict:
        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for _i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = pm.get_prompt(PromptNames.MANAGER_RISK, variables={
            "trader_plan": trader_plan,
            "past_memory_str": past_memory_str,
            "history": history,
        })

        try:
            response = llm.invoke(prompt)
            content = response.content
        except Exception as e:
            logger.exception("Risk Manager LLM invoke failed")
            content = f"HOLD. Error during risk synthesis: {e}"

        # Use StateManager to update state
        from tradingagents.graph.state_manager import StateManager
        state_manager = StateManager()
        state_update = state_manager.update_risk_manager_decision(state, content)
        return state_update

    return risk_manager_node
