"""Base Agent classes for TradingAgents framework.

Provides unified interface and common functionality for all agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from tradingagents.agents.utils.agent_states import AgentState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all TradingAgents agents.
    
    Provides unified interface and common functionality:
    - Error handling
    - Logging
    - Performance monitoring
    - State access abstraction
    """
    
    def __init__(self, llm, memory=None, name: str = None):
        """Initialize the agent.
        
        Args:
            llm: Language model instance
            memory: Optional memory instance for semantic retrieval
            name: Agent name for logging
        """
        self.llm = llm
        self.memory = memory
        self.name = name or self.__class__.__name__
        self._logger = logging.getLogger(f"{__name__}.{self.name}")
    
    @abstractmethod
    def analyze(self, state: AgentState) -> dict:
        """Execute agent analysis.
        
        This is the core method that each agent must implement.
        Agent should only read from state and return analysis results.
        State updates should be handled by StateManager.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with analysis results (e.g., {"market_report": "..."})
        """
        pass
    
    def execute(self, state: AgentState) -> dict:
        """Execute agent with error handling and monitoring.
        
        This is the public interface for executing an agent.
        It wraps analyze() with error handling, logging, and monitoring.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with analysis results
        """
        try:
            self._logger.debug(f"{self.name} starting analysis")
            result = self.analyze(state)
            self._logger.debug(f"{self.name} completed analysis")
            return result
        except Exception as e:
            self._logger.exception(f"{self.name} analysis failed: {e}")
            return self._handle_error(e, state)
    
    def _handle_error(self, error: Exception, state: AgentState) -> dict:
        """Handle errors during agent execution.
        
        Args:
            error: The exception that occurred
            state: Current agent state
            
        Returns:
            Default output dictionary
        """
        # Default error handling: return empty result
        # Subclasses can override for custom error handling
        return {}
    
    def get_state_accessor(self, state: AgentState):
        """Get a state accessor for safe state access.
        
        Args:
            state: Current agent state
            
        Returns:
            StateAccessor instance
        """
        from tradingagents.graph.state_manager import StateAccessor
        return StateAccessor(state)


class BaseAnalyst(BaseAgent):
    """Base class for analyst agents (Market, News, Social, Fundamentals).
    
    Provides common functionality for all analysts:
    - Tool binding
    - Prompt management
    - Report generation
    """
    
    def __init__(self, llm, tools: list, prompt_name: str, report_field: str, name: str = None):
        """Initialize analyst.
        
        Args:
            llm: Language model instance
            tools: List of tools available to this analyst
            prompt_name: Prompt name from PromptManager
            report_field: State field name for the report (e.g., "market_report")
            name: Agent name
        """
        super().__init__(llm, name=name)
        self.tools = tools
        self.prompt_name = prompt_name
        self.report_field = report_field
    
    def analyze(self, state: AgentState) -> dict:
        """Execute analyst analysis.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with report field
        """
        from tradingagents.prompts import PromptNames, get_prompt_manager
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        
        pm = get_prompt_manager()
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        parts = pm.get_prompt_parts(self.prompt_name)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", parts["system_template"]),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        prompt = prompt.partial(
            system_message=parts["template"],
            tool_names=", ".join([tool.name for tool in self.tools]),
            current_date=current_date,
            ticker=ticker,
        )
        
        chain = prompt | self.llm.bind_tools(self.tools)
        result = chain.invoke(state["messages"])
        
        report = ""
        if len(result.tool_calls) == 0:
            report = result.content
        
        return {
            "messages": [result],
            self.report_field: report,
        }


class BaseResearcher(BaseAgent):
    """Base class for researcher agents (Bull, Bear).
    
    Provides common functionality for researchers:
    - Memory retrieval
    - Debate state management (read-only, updates via StateManager)
    - Argument generation
    """
    
    def __init__(self, llm, memory, prompt_name: str, prefix: str, name: str = None):
        """Initialize researcher.
        
        Args:
            llm: Language model instance
            memory: Memory instance for semantic retrieval
            prompt_name: Prompt name from PromptManager
            prefix: Prefix for argument (e.g., "Bull Analyst", "Bear Analyst")
            name: Agent name
        """
        super().__init__(llm, memory, name=name)
        self.prompt_name = prompt_name
        self.prefix = prefix
    
    def analyze(self, state: AgentState) -> dict:
        """Execute researcher analysis.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with argument (state updates handled by StateManager)
        """
        from tradingagents.prompts import PromptNames, get_prompt_manager
        
        pm = get_prompt_manager()
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        current_response = investment_debate_state.get("current_response", "")
        
        # Get analyst reports (using helper method)
        reports = self._get_analyst_reports(state)
        curr_situation = "\n\n".join(reports.values())
        
        # Get past memories
        past_memories = []
        if self.memory:
            past_memories = self.memory.get_memories(curr_situation, n_matches=2)
        
        past_memory_str = ""
        for rec in past_memories:
            past_memory_str += rec["recommendation"] + "\n\n"
        
        prompt = pm.get_prompt(self.prompt_name, variables={
            "market_research_report": reports.get("market", ""),
            "sentiment_report": reports.get("sentiment", ""),
            "news_report": reports.get("news", ""),
            "fundamentals_report": reports.get("fundamentals", ""),
            "history": history,
            "current_response": current_response,
            "past_memory_str": past_memory_str,
        })
        
        response = self.llm.invoke(prompt)
        argument = f"{self.prefix}: {response.content}"
        
        # Return argument only - state updates handled by StateManager
        return {
            "argument": argument,
            "agent_type": self.prefix.lower().replace(" analyst", "").replace(" ", "_"),
        }
    
    def _get_analyst_reports(self, state: AgentState) -> dict:
        """Get all analyst reports from state.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with report keys and values
        """
        return {
            "market": state.get("market_report", ""),
            "sentiment": state.get("sentiment_report", ""),
            "news": state.get("news_report", ""),
            "fundamentals": state.get("fundamentals_report", ""),
        }


class BaseDebator(BaseAgent):
    """Base class for risk debator agents (Aggressive, Conservative, Neutral).
    
    Provides common functionality for risk debators:
    - Risk debate state access
    - Argument generation
    """
    
    def __init__(self, llm, prompt_name: str, prefix: str, name: str = None):
        """Initialize debator.
        
        Args:
            llm: Language model instance
            prompt_name: Prompt name from PromptManager
            prefix: Prefix for argument (e.g., "Aggressive Analyst")
            name: Agent name
        """
        super().__init__(llm, name=name)
        self.prompt_name = prompt_name
        self.prefix = prefix
    
    def analyze(self, state: AgentState) -> dict:
        """Execute debator analysis.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with argument (state updates handled by StateManager)
        """
        from tradingagents.prompts import PromptNames, get_prompt_manager
        
        pm = get_prompt_manager()
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        
        # Get other debators' responses
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")
        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        
        # Get analyst reports
        reports = self._get_analyst_reports(state)
        trader_decision = state.get("trader_investment_plan", "")
        
        prompt = pm.get_prompt(self.prompt_name, variables={
            "trader_decision": trader_decision,
            "market_research_report": reports.get("market", ""),
            "sentiment_report": reports.get("sentiment", ""),
            "news_report": reports.get("news", ""),
            "fundamentals_report": reports.get("fundamentals", ""),
            "history": history,
            "current_conservative_response": current_conservative_response,
            "current_neutral_response": current_neutral_response,
            "current_aggressive_response": current_aggressive_response,
        })
        
        response = self.llm.invoke(prompt)
        argument = f"{self.prefix}: {response.content}"
        
        # Return argument only - state updates handled by StateManager
        return {
            "argument": argument,
            "agent_type": self.prefix.lower().replace(" analyst", "").replace(" ", "_"),
        }
    
    def _get_analyst_reports(self, state: AgentState) -> dict:
        """Get all analyst reports from state.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with report keys and values
        """
        return {
            "market": state.get("market_report", ""),
            "sentiment": state.get("sentiment_report", ""),
            "news": state.get("news_report", ""),
            "fundamentals": state.get("fundamentals_report", ""),
        }
