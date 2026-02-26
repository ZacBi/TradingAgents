from tradingagents.agents.base import BaseDebator
from tradingagents.graph.state_manager import StateManager
from tradingagents.prompts import PromptNames


class AggressiveDebator(BaseDebator):
    """Aggressive Debator agent using BaseDebator."""
    
    def __init__(self, llm):
        """Initialize Aggressive Debator.
        
        Args:
            llm: Language model instance
        """
        super().__init__(
            llm=llm,
            prompt_name=PromptNames.RISK_AGGRESSIVE,
            prefix="Aggressive Analyst",
            name="Aggressive Debator",
        )
        self.state_manager = StateManager()
    
    def analyze(self, state):
        """Execute aggressive debator analysis.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with argument
        """
        # Use base class analyze to get argument
        result = super().analyze(state)
        argument = result["argument"]
        agent_type = result["agent_type"]
        
        # Use StateManager to update state
        state_update = self.state_manager.update_risk_debate_state(state, agent_type, argument)
        return state_update


def create_aggressive_debator(llm):
    """Factory function to create Aggressive Debator.
    
    Args:
        llm: Language model instance
        
    Returns:
        Aggressive debator node function
    """
    debator = AggressiveDebator(llm)
    return debator.execute
