from tradingagents.agents.base import BaseResearcher
from tradingagents.graph.state_manager import StateManager
from tradingagents.prompts import PromptNames


class BearResearcher(BaseResearcher):
    """Bear Researcher agent using BaseResearcher."""
    
    def __init__(self, llm, memory):
        """Initialize Bear Researcher.
        
        Args:
            llm: Language model instance
            memory: Memory instance for semantic retrieval
        """
        super().__init__(
            llm=llm,
            memory=memory,
            prompt_name=PromptNames.RESEARCHER_BEAR,
            prefix="Bear Analyst",
            name="Bear Researcher",
        )
        self.state_manager = StateManager()
    
    def analyze(self, state):
        """Execute bear researcher analysis.
        
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
        state_update = self.state_manager.update_debate_state(state, agent_type, argument)
        return state_update


def create_bear_researcher(llm, memory):
    """Factory function to create Bear Researcher.
    
    Args:
        llm: Language model instance
        memory: Memory instance
        
    Returns:
        Bear researcher node function
    """
    researcher = BearResearcher(llm, memory)
    return researcher.execute
