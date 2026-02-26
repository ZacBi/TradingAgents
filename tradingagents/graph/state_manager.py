"""State Manager for TradingAgents framework.

Provides unified state management interface, eliminating redundancy and ensuring consistency.
"""

import logging
from typing import Any

from tradingagents.agents.utils.agent_states import AgentState, InvestDebateState, RiskDebateState

logger = logging.getLogger(__name__)


class StateAccessor:
    """Provides safe, cached access to state data.
    
    Eliminates redundant data access and string building.
    """
    
    def __init__(self, state: AgentState):
        """Initialize with current state.
        
        Args:
            state: Current agent state
        """
        self._state = state
        self._cache = {}
    
    def get_analyst_reports(self) -> dict:
        """Get all analyst reports (with caching).
        
        Returns:
            Dictionary with report keys and values
        """
        if "analyst_reports" not in self._cache:
            self._cache["analyst_reports"] = {
                "market": self._state.get("market_report", ""),
                "sentiment": self._state.get("sentiment_report", ""),
                "news": self._state.get("news_report", ""),
                "fundamentals": self._state.get("fundamentals_report", ""),
            }
        return self._cache["analyst_reports"]
    
    def get_situation_string(self) -> str:
        """Get situation string (with caching).
        
        Returns:
            Combined situation string from all analyst reports
        """
        if "situation_string" not in self._cache:
            reports = self.get_analyst_reports()
            self._cache["situation_string"] = (
                f"{reports['market']}\n\n"
                f"{reports['sentiment']}\n\n"
                f"{reports['news']}\n\n"
                f"{reports['fundamentals']}"
            )
        return self._cache["situation_string"]


class StateManager:
    """Unified state manager for TradingAgents.
    
    Handles all state updates, ensuring consistency and eliminating redundancy.
    """
    
    def __init__(self):
        """Initialize state manager."""
        self._logger = logging.getLogger(__name__)
    
    def update_debate_state(
        self,
        state: AgentState,
        agent_type: str,
        argument: str,
    ) -> dict:
        """Update investment debate state.
        
        Args:
            state: Current agent state
            agent_type: Agent type ("bull" or "bear")
            argument: Argument string
            
        Returns:
            Updated investment_debate_state
        """
        debate_state = state["investment_debate_state"]
        history = debate_state.get("history", "")
        count = debate_state.get("count", 0)
        
        # Build new state - only store history, not redundant fields
        new_history = history + "\n" + argument if history else argument
        
        new_state: InvestDebateState = {
            "history": new_history,
            "bull_history": debate_state.get("bull_history", ""),
            "bear_history": debate_state.get("bear_history", ""),
            "current_response": argument,
            "judge_decision": debate_state.get("judge_decision", ""),
            "count": count + 1,
        }
        
        # Update agent-specific history
        if agent_type == "bull":
            new_state["bull_history"] = (debate_state.get("bull_history", "") + "\n" + argument).strip()
        elif agent_type == "bear":
            new_state["bear_history"] = (debate_state.get("bear_history", "") + "\n" + argument).strip()
        
        return {"investment_debate_state": new_state}
    
    def update_risk_debate_state(
        self,
        state: AgentState,
        agent_type: str,
        argument: str,
    ) -> dict:
        """Update risk debate state.
        
        Args:
            state: Current agent state
            agent_type: Agent type ("aggressive", "conservative", or "neutral")
            argument: Argument string
            
        Returns:
            Updated risk_debate_state
        """
        risk_state = state["risk_debate_state"]
        history = risk_state.get("history", "")
        count = risk_state.get("count", 0)
        
        # Build new state - only store history, not redundant fields
        new_history = history + "\n" + argument if history else argument
        
        new_state: RiskDebateState = {
            "history": new_history,
            "aggressive_history": risk_state.get("aggressive_history", ""),
            "conservative_history": risk_state.get("conservative_history", ""),
            "neutral_history": risk_state.get("neutral_history", ""),
            "latest_speaker": agent_type.capitalize(),
            "current_aggressive_response": risk_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_state.get("current_neutral_response", ""),
            "judge_decision": risk_state.get("judge_decision", ""),
            "count": count + 1,
        }
        
        # Update agent-specific history and current response
        if agent_type == "aggressive":
            new_state["aggressive_history"] = (risk_state.get("aggressive_history", "") + "\n" + argument).strip()
            new_state["current_aggressive_response"] = argument
        elif agent_type == "conservative":
            new_state["conservative_history"] = (risk_state.get("conservative_history", "") + "\n" + argument).strip()
            new_state["current_conservative_response"] = argument
        elif agent_type == "neutral":
            new_state["neutral_history"] = (risk_state.get("neutral_history", "") + "\n" + argument).strip()
            new_state["current_neutral_response"] = argument
        
        return {"risk_debate_state": new_state}
    
    def update_research_manager_decision(
        self,
        state: AgentState,
        decision: str,
    ) -> dict:
        """Update research manager decision.
        
        Args:
            state: Current agent state
            decision: Research manager decision
            
        Returns:
            Updated state with investment_plan
        """
        debate_state = state["investment_debate_state"]
        new_debate_state: InvestDebateState = {
            "history": debate_state.get("history", ""),
            "bull_history": debate_state.get("bull_history", ""),
            "bear_history": debate_state.get("bear_history", ""),
            "current_response": decision,
            "judge_decision": decision,
            "count": debate_state.get("count", 0),
        }
        
        return {
            "investment_debate_state": new_debate_state,
            "investment_plan": decision,
        }
    
    def update_risk_manager_decision(
        self,
        state: AgentState,
        decision: str,
    ) -> dict:
        """Update risk manager decision.
        
        Args:
            state: Current agent state
            decision: Risk manager decision
            
        Returns:
            Updated state with final_trade_decision
        """
        risk_state = state["risk_debate_state"]
        new_risk_state: RiskDebateState = {
            "history": risk_state.get("history", ""),
            "aggressive_history": risk_state.get("aggressive_history", ""),
            "conservative_history": risk_state.get("conservative_history", ""),
            "neutral_history": risk_state.get("neutral_history", ""),
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_state.get("current_neutral_response", ""),
            "judge_decision": decision,
            "count": risk_state.get("count", 0),
        }
        
        return {
            "risk_debate_state": new_risk_state,
            "final_trade_decision": decision,
        }
