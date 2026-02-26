"""Graph Builder for TradingAgents workflow.

Simplifies graph construction using Builder pattern.
"""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from tradingagents.agents.utils.agent_states import AgentState

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builder for constructing TradingAgents workflow graph.
    
    Simplifies complex graph construction logic.
    """
    
    def __init__(self):
        """Initialize graph builder."""
        self.workflow = StateGraph(AgentState)
        self._nodes = {}
        self._edges = []
        self._conditional_edges = []
    
    def add_node(self, name: str, node_func: Any):
        """Add a node to the graph.
        
        Args:
            name: Node name
            node_func: Node function
        """
        self.workflow.add_node(name, node_func)
        self._nodes[name] = node_func
        logger.debug(f"Added node: {name}")
    
    def add_edge(self, from_node: str, to_node: str):
        """Add an edge to the graph.
        
        Args:
            from_node: Source node name
            to_node: Target node name
        """
        self.workflow.add_edge(from_node, to_node)
        self._edges.append((from_node, to_node))
        logger.debug(f"Added edge: {from_node} -> {to_node}")
    
    def add_conditional_edges(
        self,
        from_node: str,
        condition_func: Any,
        edge_map: dict,
    ):
        """Add conditional edges to the graph.
        
        Args:
            from_node: Source node name
            condition_func: Condition function
            edge_map: Dictionary mapping condition results to target nodes
        """
        self.workflow.add_conditional_edges(from_node, condition_func, edge_map)
        self._conditional_edges.append((from_node, condition_func, edge_map))
        logger.debug(f"Added conditional edges from: {from_node}")
    
    def add_parallel_analysts(self, analyst_nodes: dict, next_node: str):
        """Add parallel analyst nodes.
        
        Args:
            analyst_nodes: Dictionary of analyst_type -> node_function
            next_node: Next node after analysts complete
        """
        from langgraph.types import Send
        
        selected = list(analyst_nodes.keys())
        self.workflow.add_conditional_edges(
            START,
            lambda state: [Send(f"Analyst_{t}", state) for t in selected],
            [f"Analyst_{t}" for t in selected],
        )
        
        for analyst_type in selected:
            self.add_edge(f"Analyst_{analyst_type}", next_node)
    
    def build(self, checkpointer=None):
        """Build and compile the graph.
        
        Args:
            checkpointer: Optional checkpointer for state persistence
            
        Returns:
            Compiled graph
        """
        if checkpointer is not None:
            return self.workflow.compile(checkpointer=checkpointer)
        return self.workflow.compile()
