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
            Latest checkpoint state or None if not found
        """
        if not self.checkpointer:
            self._logger.warning("No checkpointer available for recovery")
            return None
        
        try:
            # Get latest checkpoint using LangGraph API
            # Note: This is a simplified version - actual implementation depends on LangGraph API
            # In practice, you would use checkpointer.get() or similar method
            checkpoints = list(self.checkpointer.list(thread_id, limit=1))
            if checkpoints:
                checkpoint = checkpoints[0]
                return self.checkpointer.get({"configurable": {"thread_id": thread_id}})
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
            checkpoints = list(self.checkpointer.list(thread_id, limit=limit))
            return checkpoints
        except Exception as e:
            self._logger.exception("Failed to list checkpoints: %s", e)
            return []
    
    def recover_state(self, thread_id: str) -> Optional[AgentState]:
        """Recover agent state from latest checkpoint.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Recovered agent state or None if recovery failed
        """
        checkpoint = self.get_latest_checkpoint(thread_id)
        if not checkpoint:
            self._logger.info("No checkpoint found for thread_id: %s", thread_id)
            return None
        
        try:
            # Extract state from checkpoint
            # LangGraph checkpoints contain state in a specific format
            state = checkpoint.get("values", {})
            self._logger.info("Recovered state from checkpoint for thread_id: %s", thread_id)
            return state
        except Exception as e:
            self._logger.exception("Failed to recover state: %s", e)
            return None
    
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
