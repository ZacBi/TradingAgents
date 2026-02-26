"""Route Resolver for TradingAgents graph.

Handles routing decisions based on condition evaluation results.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RouteResolver:
    """Resolves routing decisions based on conditions.
    
    Separates routing logic from condition evaluation.
    """
    
    def __init__(self, condition_evaluator: Any):
        """Initialize route resolver.
        
        Args:
            condition_evaluator: ConditionEvaluator instance
        """
        self.condition_evaluator = condition_evaluator
        self._logger = logging.getLogger(__name__)
    
    def resolve_debate_route(self, state: Any, expert_enabled: bool = False) -> str:
        """Resolve route after debate evaluation.
        
        Args:
            state: Current agent state
            expert_enabled: Whether expert team is enabled
            
        Returns:
            Next node name
        """
        if self.condition_evaluator.should_continue_debate(state):
            # Continue debate - alternate between Bull and Bear
            current_speaker = state.get("investment_debate_state", {}).get("current_response", "")
            if "Bull Analyst" in current_speaker:
                return "Bear Researcher"
            else:
                return "Bull Researcher"
        else:
            # End debate - go to Research Manager or Experts
            if expert_enabled:
                return "Experts"
            return "Research Manager"
    
    def resolve_risk_route(self, state: Any, current_node: str) -> str:
        """Resolve route after risk analysis evaluation.
        
        Args:
            state: Current agent state
            current_node: Current node name
            
        Returns:
            Next node name
        """
        if self.condition_evaluator.should_continue_risk_analysis(state):
            # Continue risk analysis - cycle through debators
            if current_node == "Aggressive Analyst":
                return "Conservative Analyst"
            elif current_node == "Conservative Analyst":
                return "Neutral Analyst"
            else:  # Neutral Analyst
                return "Aggressive Analyst"
        else:
            # End risk analysis - go to Risk Judge
            return "Risk Judge"
    
    def resolve_deep_research_route(self, state: Any) -> str:
        """Resolve route for deep research decision.
        
        Args:
            state: Current agent state
            
        Returns:
            Next node name ("Deep Research" or "Bull Researcher")
        """
        if self.condition_evaluator.should_run_deep_research(state):
            return "Deep Research"
        return "Bull Researcher"
