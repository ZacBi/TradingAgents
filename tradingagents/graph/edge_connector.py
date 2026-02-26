"""Edge Connector for TradingAgents graph.

Handles edge connection logic, simplifying complex routing.
"""

import logging
from typing import Any

from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)


class EdgeConnector:
    """Handles edge connection for TradingAgents graph.
    
    Simplifies complex edge connection logic.
    """
    
    def __init__(self, conditional_logic: Any):
        """Initialize edge connector.
        
        Args:
            conditional_logic: ConditionalLogic instance for routing decisions
        """
        self.conditional_logic = conditional_logic
        self._logger = logging.getLogger(__name__)
    
    def connect_analysts_to_next(
        self,
        workflow: StateGraph,
        selected_analysts: list,
        next_after_analysts: str,
    ):
        """Connect analysts to next node.
        
        Args:
            workflow: Workflow graph
            selected_analysts: List of selected analyst types
            next_after_analysts: Next node after analysts
        """
        from langgraph.types import Send
        
        _selected = list(selected_analysts)
        workflow.add_conditional_edges(
            START,
            lambda state: [Send(f"Analyst_{t}", state) for t in _selected],
            [f"Analyst_{t}" for t in selected_analysts],
        )
        for analyst_type in selected_analysts:
            workflow.add_edge(f"Analyst_{analyst_type}", next_after_analysts)
    
    def connect_valuation_and_deep(
        self,
        workflow: StateGraph,
        valuation_enabled: bool,
        use_deep_branch: bool,
    ):
        """Connect valuation and deep research nodes.
        
        Args:
            workflow: Workflow graph
            valuation_enabled: Whether valuation is enabled
            use_deep_branch: Whether deep research is enabled
        """
        if valuation_enabled and use_deep_branch:
            workflow.add_conditional_edges(
                "Valuation Analyst",
                self.conditional_logic.should_run_deep_research,
                {"Deep Research": "Deep Research", "Bull Researcher": "Bull Researcher"},
            )
            workflow.add_edge("Deep Research", "Bull Researcher")
        elif valuation_enabled:
            workflow.add_edge("Valuation Analyst", "Bull Researcher")
        elif use_deep_branch:
            workflow.add_conditional_edges(
                "After Analysts",
                self.conditional_logic.should_run_deep_research,
                {"Deep Research": "Deep Research", "Bull Researcher": "Bull Researcher"},
            )
            workflow.add_edge("Deep Research", "Bull Researcher")
    
    def connect_debate_and_risk(
        self,
        workflow: StateGraph,
        expert_team_node: Any,
    ):
        """Connect debate and risk analysis nodes.
        
        Args:
            workflow: Workflow graph
            expert_team_node: Optional expert team node
        """
        # Bull/Bear debate
        bull_targets = {"Bear Researcher": "Bear Researcher", "Research Manager": "Research Manager"}
        if expert_team_node is not None:
            bull_targets["Experts"] = "Experts"
        workflow.add_conditional_edges(
            "Bull Researcher", self.conditional_logic.should_continue_debate, bull_targets
        )
        
        bear_targets = {"Bull Researcher": "Bull Researcher", "Research Manager": "Research Manager"}
        if expert_team_node is not None:
            bear_targets["Experts"] = "Experts"
        workflow.add_conditional_edges(
            "Bear Researcher", self.conditional_logic.should_continue_debate, bear_targets
        )
        
        if expert_team_node is not None:
            workflow.add_edge("Experts", "Research Manager")
        
        # Research -> Trader
        workflow.add_edge("Research Manager", "Trader")
        
        # Trader -> Risk
        workflow.add_edge("Trader", "Aggressive Analyst")
        
        # Risk debate
        for from_node, to_options in [
            ("Aggressive Analyst", {"Conservative Analyst": "Conservative Analyst", "Risk Judge": "Risk Judge"}),
            ("Conservative Analyst", {"Neutral Analyst": "Neutral Analyst", "Risk Judge": "Risk Judge"}),
            ("Neutral Analyst", {"Aggressive Analyst": "Aggressive Analyst", "Risk Judge": "Risk Judge"}),
        ]:
            workflow.add_conditional_edges(
                from_node, self.conditional_logic.should_continue_risk_analysis, to_options
            )
        
        # Risk Judge -> END
        workflow.add_edge("Risk Judge", END)
