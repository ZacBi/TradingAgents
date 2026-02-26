"""Recovery Engine for TradingAgents.

Handles state recovery and error recovery for long-run agents.
"""

import logging
from typing import Any, Optional

from tradingagents.agents.utils.agent_states import AgentState

logger = logging.getLogger(__name__)


class RecoveryEngine:
    """Engine for recovering agent state from checkpoints.
    
    Enables long-run agents to resume from previous states after crashes or restarts.
    """
    
    def __init__(self, checkpointer: Any):
        """Initialize recovery engine.
        
        Args:
            checkpointer: LangGraph checkpointer instance
        """
        self.checkpointer = checkpointer
        self._logger = logging.getLogger(__name__)
    
    def get_latest_checkpoint(self, thread_id: str) -> Optional[dict]:
        """Get the latest checkpoint for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Latest checkpoint tuple or None if not found
        """
        if not self.checkpointer:
            self._logger.warning("No checkpointer available for recovery")
            return None
        
        try:
            # Use LangGraph checkpoint API with proper configuration format
            config = {"configurable": {"thread_id": thread_id}}
            
            # Get the latest checkpoint using get_tuple (returns checkpoint tuple)
            # If get_tuple doesn't exist, try get
            if hasattr(self.checkpointer, "get_tuple"):
                checkpoint_tuple = self.checkpointer.get_tuple(config)
                if checkpoint_tuple:
                    return {
                        "checkpoint_id": checkpoint_tuple.get("checkpoint_id"),
                        "parent_checkpoint_id": checkpoint_tuple.get("parent_checkpoint_id"),
                        "values": checkpoint_tuple.get("channel_values", {}),
                        "metadata": checkpoint_tuple.get("metadata", {}),
                    }
            elif hasattr(self.checkpointer, "get"):
                # Fallback to get method
                checkpoint = self.checkpointer.get(config)
                if checkpoint:
                    return checkpoint
            
            # If no checkpoint found, try listing to see if any exist
            checkpoints = list(self.checkpointer.list(config, limit=1))
            if checkpoints:
                # Use the first checkpoint's ID to get full checkpoint
                latest_checkpoint_id = checkpoints[0].get("checkpoint_id")
                if latest_checkpoint_id:
                    config_with_id = {"configurable": {"thread_id": thread_id, "checkpoint_id": latest_checkpoint_id}}
                    if hasattr(self.checkpointer, "get_tuple"):
                        checkpoint_tuple = self.checkpointer.get_tuple(config_with_id)
                        if checkpoint_tuple:
                            return {
                                "checkpoint_id": checkpoint_tuple.get("checkpoint_id"),
                                "parent_checkpoint_id": checkpoint_tuple.get("parent_checkpoint_id"),
                                "values": checkpoint_tuple.get("channel_values", {}),
                                "metadata": checkpoint_tuple.get("metadata", {}),
                            }
                    elif hasattr(self.checkpointer, "get"):
                        return self.checkpointer.get(config_with_id)
            
            return None
        except Exception as e:
            self._logger.exception("Failed to get latest checkpoint: %s", e)
            return None
    
    def list_checkpoints(self, thread_id: str, limit: int = 10) -> list:
        """List available checkpoints for a thread.
        
        Args:
            thread_id: Thread identifier
            limit: Maximum number of checkpoints to return
            
        Returns:
            List of checkpoint metadata
        """
        if not self.checkpointer:
            return []
        
        try:
            # Use proper configuration format for list API
            config = {"configurable": {"thread_id": thread_id}}
            checkpoints = list(self.checkpointer.list(config, limit=limit))
            return checkpoints
        except Exception as e:
            self._logger.exception("Failed to list checkpoints: %s", e)
            return []
    
    def recover_state(self, thread_id: str, merge_with_initial: Optional[AgentState] = None) -> Optional[AgentState]:
        """Recover agent state from latest checkpoint.
        
        Args:
            thread_id: Thread identifier
            merge_with_initial: Optional initial state to merge with recovered state
            
        Returns:
            Recovered agent state or None if recovery failed
        """
        checkpoint = self.get_latest_checkpoint(thread_id)
        if not checkpoint:
            self._logger.info("No checkpoint found for thread_id: %s", thread_id)
            return merge_with_initial
        
        try:
            # Extract state from checkpoint
            # LangGraph checkpoints contain state in channel_values or values
            recovered_state = checkpoint.get("values") or checkpoint.get("channel_values", {})
            if not recovered_state:
                self._logger.warning("Checkpoint found but no state values for thread_id: %s", thread_id)
                return merge_with_initial
            
            # If initial state provided, merge intelligently
            if merge_with_initial:
                merged_state = self._merge_states(merge_with_initial, recovered_state)
                self._logger.info("Merged recovered state with initial state for thread_id: %s", thread_id)
                return merged_state
            
            self._logger.info("Recovered state from checkpoint for thread_id: %s", thread_id)
            return recovered_state
        except Exception as e:
            self._logger.exception("Failed to recover state: %s", e)
            return merge_with_initial
    
    def _merge_states(self, initial_state: AgentState, recovered_state: AgentState) -> AgentState:
        """Merge initial state with recovered state intelligently.
        
        Strategy:
        - Keep initial state for immutable fields (company_of_interest, trade_date)
        - Prefer recovered state for analysis results (reports, decisions)
        - Merge debate states carefully (preserve history)
        
        Args:
            initial_state: Initial state to merge
            recovered_state: Recovered state from checkpoint
            
        Returns:
            Merged state
        """
        merged = initial_state.copy()
        
        # Keep initial immutable fields
        # company_of_interest and trade_date should come from initial state
        
        # Prefer recovered state for analysis results if they exist
        report_fields = ["market_report", "sentiment_report", "news_report", "fundamentals_report"]
        for field in report_fields:
            if recovered_state.get(field) and not initial_state.get(field):
                merged[field] = recovered_state[field]
        
        # Merge debate states - preserve history but allow continuation
        if "investment_debate_state" in recovered_state:
            recovered_debate = recovered_state["investment_debate_state"]
            if "investment_debate_state" not in merged or not merged["investment_debate_state"].get("history"):
                # If initial state has no debate history, use recovered
                merged["investment_debate_state"] = recovered_debate
            else:
                # Merge debate histories
                initial_debate = merged["investment_debate_state"]
                merged["investment_debate_state"] = {
                    "history": recovered_debate.get("history", initial_debate.get("history", "")),
                    "bull_history": recovered_debate.get("bull_history", initial_debate.get("bull_history", "")),
                    "bear_history": recovered_debate.get("bear_history", initial_debate.get("bear_history", "")),
                    "current_response": recovered_debate.get("current_response", initial_debate.get("current_response", "")),
                    "judge_decision": recovered_debate.get("judge_decision", initial_debate.get("judge_decision", "")),
                    "count": recovered_debate.get("count", initial_debate.get("count", 0)),
                }
        
        # Similar merge for risk_debate_state
        if "risk_debate_state" in recovered_state:
            recovered_risk = recovered_state["risk_debate_state"]
            if "risk_debate_state" not in merged or not merged["risk_debate_state"].get("history"):
                merged["risk_debate_state"] = recovered_risk
            else:
                initial_risk = merged["risk_debate_state"]
                merged["risk_debate_state"] = {
                    "history": recovered_risk.get("history", initial_risk.get("history", "")),
                    "aggressive_history": recovered_risk.get("aggressive_history", initial_risk.get("aggressive_history", "")),
                    "conservative_history": recovered_risk.get("conservative_history", initial_risk.get("conservative_history", "")),
                    "neutral_history": recovered_risk.get("neutral_history", initial_risk.get("neutral_history", "")),
                    "latest_speaker": recovered_risk.get("latest_speaker", initial_risk.get("latest_speaker", "")),
                    "current_aggressive_response": recovered_risk.get("current_aggressive_response", initial_risk.get("current_aggressive_response", "")),
                    "current_conservative_response": recovered_risk.get("current_conservative_response", initial_risk.get("current_conservative_response", "")),
                    "current_neutral_response": recovered_risk.get("current_neutral_response", initial_risk.get("current_neutral_response", "")),
                    "judge_decision": recovered_risk.get("judge_decision", initial_risk.get("judge_decision", "")),
                    "count": recovered_risk.get("count", initial_risk.get("count", 0)),
                }
        
        # Prefer recovered decisions if they exist
        if recovered_state.get("investment_plan") and not merged.get("investment_plan"):
            merged["investment_plan"] = recovered_state["investment_plan"]
        if recovered_state.get("trader_investment_plan") and not merged.get("trader_investment_plan"):
            merged["trader_investment_plan"] = recovered_state["trader_investment_plan"]
        if recovered_state.get("final_trade_decision") and not merged.get("final_trade_decision"):
            merged["final_trade_decision"] = recovered_state["final_trade_decision"]
        
        return merged
    
    def can_recover(self, thread_id: str) -> bool:
        """Check if recovery is possible for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            True if recovery is possible, False otherwise
        """
        if not self.checkpointer:
            return False
        
        checkpoint = self.get_latest_checkpoint(thread_id)
        return checkpoint is not None
    
    def get_checkpoint_metadata(self, thread_id: str) -> Optional[dict]:
        """Get metadata about the latest checkpoint.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Checkpoint metadata or None
        """
        checkpoint = self.get_latest_checkpoint(thread_id)
        if not checkpoint:
            return None
        
        return {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint.get("checkpoint_id"),
            "parent_checkpoint_id": checkpoint.get("parent_checkpoint_id"),
            "metadata": checkpoint.get("metadata", {}),
        }
