"""Condition Evaluator for TradingAgents graph.

Handles condition evaluation logic, separated from routing decisions.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluates conditions for graph routing.
    
    Separates condition evaluation from routing logic.
    """
    
    def __init__(self, config: dict = None):
        """Initialize condition evaluator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.max_debate_rounds = self.config.get("max_debate_rounds", 3)
        self.max_risk_rounds = self.config.get("max_risk_rounds", 3)
        self._logger = logging.getLogger(__name__)
    
    def should_continue_debate(self, state: Any) -> bool:
        """Evaluate if debate should continue.
        
        Args:
            state: Current agent state
            
        Returns:
            True if debate should continue, False otherwise
        """
        debate_state = state.get("investment_debate_state", {})
        count = debate_state.get("count", 0)
        
        # Check round limit
        if count >= self.max_debate_rounds:
            return False
        
        # Check convergence (simplified - can be enhanced)
        # For now, just check if we've had enough rounds
        return count < self.max_debate_rounds
    
    def should_continue_risk_analysis(self, state: Any) -> bool:
        """Evaluate if risk analysis should continue.
        
        Args:
            state: Current agent state
            
        Returns:
            True if risk analysis should continue, False otherwise
        """
        risk_state = state.get("risk_debate_state", {})
        count = risk_state.get("count", 0)
        
        # Check round limit
        if count >= self.max_risk_rounds:
            return False
        
        return count < self.max_risk_rounds
    
    def should_run_deep_research(self, state: Any) -> bool:
        """Evaluate if deep research should run.
        
        Args:
            state: Current agent state
            
        Returns:
            True if deep research should run, False otherwise
        """
        # Simplified logic - can be enhanced based on state
        # For now, check if deep research is enabled
        return self.config.get("deep_research_enabled", False)
