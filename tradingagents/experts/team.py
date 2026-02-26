# TradingAgents/experts/team.py
"""Expert team node: runs selected experts and aggregates evaluations."""

import logging
from collections.abc import Callable
from typing import Any

from .selector import ExpertSelector

logger = logging.getLogger(__name__)


def create_expert_team_node(
    llm,
    config: dict[str, Any],
    prompt_manager: object | None = None,
) -> Callable:
    """
    Factory for a single graph node that runs selected experts and merges results.

    Uses ExpertSelector to choose experts, then runs each expert's factory
    in sequence and aggregates expert_evaluations into state.

    Args:
        llm: Language model instance
        config: Configuration with max_experts, expert_selection_mode, selected_experts, etc.
        prompt_manager: Optional PromptManager for expert prompts

    Returns:
        A node function (state) -> state_update with expert_evaluations.
    """
    selector = ExpertSelector(config)

    def expert_team_node(state: dict) -> dict:
        ticker = state.get("company_of_interest") or ""
        stock_info = state.get("stock_info") or {}
        user_override = config.get("selected_experts")

        selected = selector.select(ticker, stock_info, user_override=user_override)
        if not selected:
            logger.warning("Expert selector returned no experts for ticker=%s", ticker)
            return {"expert_evaluations": state.get("expert_evaluations", [])}

        evaluations = list(state.get("expert_evaluations", []))
        current_state = dict(state)

        for profile in selected:
            try:
                node_fn = profile.factory(llm, None, prompt_manager)
                out = node_fn({**current_state, "expert_evaluations": evaluations})
                evaluations = out.get("expert_evaluations", evaluations)
                current_state = {**current_state, **out}
            except Exception as e:
                logger.warning("Expert %s failed: %s", profile.id, e)

        return {"expert_evaluations": evaluations}
    return expert_team_node
