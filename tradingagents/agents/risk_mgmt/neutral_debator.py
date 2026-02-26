from tradingagents.agents.base import BaseDebator
from tradingagents.graph.state_manager import StateManager
from tradingagents.prompts import PromptNames


class NeutralDebator(BaseDebator):
    """Neutral Debator agent using BaseDebator."""
    
    def __init__(self, llm):
        """Initialize Neutral Debator.
        
        Args:
            llm: Language model instance
        """
        super().__init__(
            llm=llm,
            prompt_name=PromptNames.RISK_NEUTRAL,
            prefix="Neutral Analyst",
            name="Neutral Debator",
        )
        self.state_manager = StateManager()
    
    def analyze(self, state):
        """Execute neutral debator analysis.
        
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


def create_neutral_debator(llm):
    """Factory function to create Neutral Debator.
    
    Args:
        llm: Language model instance
        
    Returns:
        Neutral debator node function
    """
    debator = NeutralDebator(llm)
    return debator.execute
