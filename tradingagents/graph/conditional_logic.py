# TradingAgents/graph/conditional_logic.py

import logging

from tradingagents.agents.utils.agent_states import AgentState

logger = logging.getLogger(__name__)


from .condition_evaluator import ConditionEvaluator
from .route_resolver import RouteResolver


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(
        self,
        max_debate_rounds: int = 1,
        max_risk_discuss_rounds: int = 1,
        config: dict | None = None,
    ):
        """
        Initialize with configuration parameters.

        Args:
            max_debate_rounds: Maximum rounds of bull/bear debate
            max_risk_discuss_rounds: Maximum rounds of risk discussion
            config: Full configuration dict for convergence detection
        """
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds
        self._config = config or {}
        
        # Initialize condition evaluator and route resolver
        config_for_evaluator = self._config.copy()
        config_for_evaluator["max_debate_rounds"] = max_debate_rounds
        config_for_evaluator["max_risk_rounds"] = max_risk_discuss_rounds
        self.condition_evaluator = ConditionEvaluator(config_for_evaluator)
        self.route_resolver = RouteResolver(self.condition_evaluator)

        # Phase 3: Initialize convergence detector if enabled
        self._convergence_detector = None
        if self._config.get("debate_convergence_enabled", False):
            try:
                from .convergence import ConvergenceDetector
                self._convergence_detector = ConvergenceDetector(self._config)
                logger.info("Convergence detector initialized")
            except Exception as e:
                logger.warning("Failed to initialize convergence detector: %s", e)

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_market"
        return "Msg Clear Market"

    def should_continue_social(self, state: AgentState):
        """Determine if social media analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        """Determine if fundamentals analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_debate(self, state: AgentState) -> str:
        """
        Determine if debate should continue.

        Uses convergence detection if enabled, otherwise uses RouteResolver.
        """
        debate_state = state["investment_debate_state"]
        current_count = debate_state.get("count", 0)

        # Phase 3: Check semantic convergence if enabled
        if self._convergence_detector is not None:
            # Build history list from debate state
            history = debate_state.get("history", "")
            history_list = [h.strip() for h in history.split("\n") if h.strip()]

            should_stop, reason = self._convergence_detector.should_stop(
                history_list, current_count
            )

            if should_stop:
                logger.info("Debate stopping: reason=%s, rounds=%d", reason, current_count // 2)
                return self._after_debate_target(state)

        # Use RouteResolver for routing decision
        expert_enabled = self._config.get("experts_enabled", False)
        return self.route_resolver.resolve_debate_route(state, expert_enabled)

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue.
        
        Uses RouteResolver for routing decision.
        """
        risk_state = state["risk_debate_state"]
        current_speaker = risk_state.get("latest_speaker", "Aggressive")
        
        # Map speaker to node name
        node_map = {
            "Aggressive": "Aggressive Analyst",
            "Conservative": "Conservative Analyst",
            "Neutral": "Neutral Analyst",
        }
        current_node = node_map.get(current_speaker.split()[0], "Aggressive Analyst")
        
        return self.route_resolver.resolve_risk_route(state, current_node)

    def _after_debate_target(self, state: AgentState) -> str:
        """After debate ends, route to Experts (if enabled) or Research Manager."""
        if self.should_route_to_experts(state) == "Experts":
            return "Experts"
        return "Research Manager"

    def should_route_to_experts(self, state: AgentState) -> str:
        """
        Determine if analysis should route to expert evaluation.

        Called after debate concludes to decide if experts should evaluate.
        Returns "Experts" or "Trader" based on configuration.
        """
        if not self._config.get("experts_enabled", False):
            return "Trader"

        # Check if experts have already evaluated
        if state.get("expert_evaluations"):
            return "Trader"

        return "Experts"

    def should_run_deep_research(self, state: AgentState) -> str:
        """
        Determine if deep research should run.

        Called after analysts complete to decide if deep research is needed.
        Uses RouteResolver for routing decision.
        """
        # Check if deep research already completed
        if state.get("deep_research_report"):
            return "Bull Researcher"

        # Use RouteResolver for routing decision
        return self.route_resolver.resolve_deep_research_route(state)
