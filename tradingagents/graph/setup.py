# TradingAgents/graph/setup.py

from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Send

from tradingagents.agents import (
    create_aggressive_debator,
    create_bear_researcher,
    create_bull_researcher,
    create_conservative_debator,
    create_fundamentals_analyst,
    create_market_analyst,
    create_neutral_debator,
    create_news_analyst,
    create_research_manager,
    create_risk_manager,
    create_social_media_analyst,
    create_trader,
)
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.experts import create_expert_team_node
from tradingagents.research import create_deep_research_agent

from .conditional_logic import ConditionalLogic
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

    def _build_analyst_nodes(self, selected_analysts: list) -> tuple[dict, dict]:
        """Build analyst callables and tool nodes for selected analyst types."""
        analyst_nodes = {}
        tool_nodes = {}
        creators = {
            "market": (create_market_analyst, "market"),
            "social": (create_social_media_analyst, "social"),
            "news": (create_news_analyst, "news"),
            "fundamentals": (create_fundamentals_analyst, "fundamentals"),
        }
        for key in selected_analysts:
            if key in creators:
                create_fn, tool_key = creators[key]
                analyst_nodes[key] = create_fn(self.quick_thinking_llm)
                tool_nodes[key] = self.tool_nodes[tool_key]
        return analyst_nodes, tool_nodes

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

    def _add_core_nodes(
        self,
        workflow: StateGraph,
        valuation_node,
        deep_research_node,
        expert_team_node,
        bull_researcher_node,
        bear_researcher_node,
        research_manager_node,
        trader_node,
        aggressive_analyst,
        neutral_analyst,
        conservative_analyst,
        risk_manager_node,
    ) -> None:
        """Register all non-analyst nodes on the workflow."""
        if valuation_node is not None:
            workflow.add_node("Valuation Analyst", valuation_node)
        if deep_research_node is not None:
            workflow.add_node("Deep Research", deep_research_node)
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        if expert_team_node is not None:
            workflow.add_node("Experts", expert_team_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Aggressive Analyst", aggressive_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Conservative Analyst", conservative_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

    def _connect_analysts_to_next(
        self, workflow: StateGraph, selected_analysts: list, next_after_analysts: str
    ) -> None:
        """Add START→analysts and analysts→next_after_analysts edges."""
        _selected = list(selected_analysts)
        workflow.add_conditional_edges(
            START,
            lambda state: [Send(f"Analyst_{t}", state) for t in _selected],
            [f"Analyst_{t}" for t in selected_analysts],
        )
        for analyst_type in selected_analysts:
            workflow.add_edge(f"Analyst_{analyst_type}", next_after_analysts)

    def _connect_valuation_and_deep(
        self, workflow: StateGraph, valuation_enabled: bool, use_deep_branch: bool
    ) -> None:
        """Add edges from Valuation/After Analysts to Deep Research or Bull Researcher."""
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

    def _connect_debate_and_risk(self, workflow: StateGraph, expert_team_node) -> None:
        """Add debate (Bull/Bear/Experts) and risk chain edges."""
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
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Aggressive Analyst")
        for from_node, to_options in [
            ("Aggressive Analyst", {"Conservative Analyst": "Conservative Analyst", "Risk Judge": "Risk Judge"}),
            ("Conservative Analyst", {"Neutral Analyst": "Neutral Analyst", "Risk Judge": "Risk Judge"}),
            ("Neutral Analyst", {"Aggressive Analyst": "Aggressive Analyst", "Risk Judge": "Risk Judge"}),
        ]:
            workflow.add_conditional_edges(
                from_node, self.conditional_logic.should_continue_risk_analysis, to_options
            )
        workflow.add_edge("Risk Judge", END)

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

        analyst_nodes, tool_nodes = self._build_analyst_nodes(selected_analysts)
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)
        aggressive_analyst = create_aggressive_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        conservative_analyst = create_conservative_debator(self.quick_thinking_llm)
        risk_manager_node = create_risk_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )

        workflow = StateGraph(AgentState)
        valuation_node, deep_research_node, expert_team_node = self._create_optional_nodes()
        valuation_enabled = valuation_node is not None
        use_deep_branch = deep_research_node is not None

        for analyst_type in selected_analysts:
            subgraph = create_analyst_subgraph(
                analyst_nodes[analyst_type], tool_nodes[analyst_type]
            )
            workflow.add_node(
                f"Analyst_{analyst_type}", create_analyst_runner(analyst_type, subgraph)
            )
        self._add_core_nodes(
            workflow,
            valuation_node,
            deep_research_node,
            expert_team_node,
            bull_researcher_node,
            bear_researcher_node,
            research_manager_node,
            trader_node,
            aggressive_analyst,
            neutral_analyst,
            conservative_analyst,
            risk_manager_node,
        )

        if valuation_enabled:
            next_after_analysts = "Valuation Analyst"
        elif use_deep_branch:
            workflow.add_node("After Analysts", lambda s: s)
            next_after_analysts = "After Analysts"
        else:
            next_after_analysts = "Bull Researcher"
        self._connect_analysts_to_next(workflow, selected_analysts, next_after_analysts)
        self._connect_valuation_and_deep(workflow, valuation_enabled, use_deep_branch)
        self._connect_debate_and_risk(workflow, expert_team_node)

        if self.checkpointer is not None:
            return workflow.compile(checkpointer=self.checkpointer)
        return workflow.compile()
