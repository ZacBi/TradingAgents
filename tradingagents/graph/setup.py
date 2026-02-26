# TradingAgents/graph/setup.py

from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.experts import create_expert_team_node
from tradingagents.research import create_deep_research_agent

from .conditional_logic import ConditionalLogic
from .edge_connector import EdgeConnector
from .graph_builder import GraphBuilder
from .node_factory import NodeFactory
from .subgraphs.analyst_subgraph import create_analyst_runner, create_analyst_subgraph


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        tool_nodes: dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
        checkpointer=None,
        config: dict[str, Any] = None,
        prompt_manager=None,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.checkpointer = checkpointer
        self.config = config or {}
        self.prompt_manager = prompt_manager
        
        # Initialize factory and builder
        memories = {
            "bull": bull_memory,
            "bear": bear_memory,
            "trader": trader_memory,
            "invest_judge": invest_judge_memory,
            "risk_manager": risk_manager_memory,
        }
        self.node_factory = NodeFactory(
            quick_thinking_llm,
            deep_thinking_llm,
            memories,
            tool_nodes,
        )
        self.graph_builder = GraphBuilder()
        self.edge_connector = EdgeConnector(conditional_logic)
        self.order_executor = None  # Will be set externally if trading is enabled

    def _create_optional_nodes(self):
        """Create valuation, deep_research, expert_team nodes if enabled. Return (valuation, deep, expert)."""
        valuation_node = None
        if self.config.get("valuation_enabled", True):
            from tradingagents.valuation import create_valuation_node
            valuation_node = create_valuation_node(
                llm=self.quick_thinking_llm,
                prompt_manager=self.prompt_manager,
                config=self.config,
            )
        deep_research_node = None
        if self.config.get("deep_research_enabled", False):
            deep_research_node = create_deep_research_agent(
                self.quick_thinking_llm, self.config
            )
        expert_team_node = None
        if self.config.get("experts_enabled", False):
            expert_team_node = create_expert_team_node(
                self.quick_thinking_llm,
                self.config,
                self.prompt_manager,
            )
        return valuation_node, deep_research_node, expert_team_node


    def setup_graph(self, selected_analysts=None):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if selected_analysts is None:
            selected_analysts = ["market", "social", "news", "fundamentals"]
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create nodes using factory
        analyst_nodes, tool_nodes = self.node_factory.create_analyst_nodes(selected_analysts)
        core_nodes = self.node_factory.create_core_nodes()
        
        # Create optional nodes
        valuation_node, deep_research_node, expert_team_node = self._create_optional_nodes()
        valuation_enabled = valuation_node is not None
        use_deep_branch = deep_research_node is not None

        # Build graph using builder
        workflow = self.graph_builder.workflow
        
        # Add analyst subgraphs
        for analyst_type in selected_analysts:
            subgraph = create_analyst_subgraph(
                analyst_nodes[analyst_type], tool_nodes[analyst_type]
            )
            self.graph_builder.add_node(
                f"Analyst_{analyst_type}", create_analyst_runner(analyst_type, subgraph)
            )
        
        # Add core nodes
        if valuation_node is not None:
            self.graph_builder.add_node("Valuation Analyst", valuation_node)
        if deep_research_node is not None:
            self.graph_builder.add_node("Deep Research", deep_research_node)
        
        for node_name, node_func in core_nodes.items():
            self.graph_builder.add_node(node_name, node_func)
        
        if expert_team_node is not None:
            self.graph_builder.add_node("Experts", expert_team_node)
        
        # Phase 3: Add Order Executor node if trading is enabled
        if self.config.get("trading_enabled", False) and hasattr(self, "order_executor") and self.order_executor:
            order_executor_node = self.order_executor.create_order_executor_node()
            self.graph_builder.add_node("Order Executor", order_executor_node)
        
        # Connect edges
        if valuation_enabled:
            next_after_analysts = "Valuation Analyst"
        elif use_deep_branch:
            self.graph_builder.add_node("After Analysts", lambda s: s)
            next_after_analysts = "After Analysts"
        else:
            next_after_analysts = "Bull Researcher"
        
        self.edge_connector.connect_analysts_to_next(
            workflow, selected_analysts, next_after_analysts
        )
        self.edge_connector.connect_valuation_and_deep(
            workflow, valuation_enabled, use_deep_branch
        )
        self.edge_connector.connect_debate_and_risk(workflow, expert_team_node)
        
        # Phase 3: Connect Order Executor if trading is enabled
        # Note: We need to modify the edge connection in edge_connector
        # For now, we'll add Order Executor node and edges here
        if self.config.get("trading_enabled", False) and self.order_executor:
            from langgraph.graph import END
            # Add Order Executor node (already added above)
            # Modify Risk Judge -> END to Risk Judge -> Order Executor -> END
            # Since we can't remove edges, we'll add the new path
            # The edge_connector already added Risk Judge -> END, so we add Order Executor in between
            workflow.add_edge("Risk Judge", "Order Executor")
            workflow.add_edge("Order Executor", END)

        # Build and return
        return self.graph_builder.build(self.checkpointer)
