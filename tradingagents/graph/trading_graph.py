# TradingAgents/graph/trading_graph.py

import os
import logging
from pathlib import Path
import json
from datetime import date
from typing import Dict, Any, Tuple, List, Optional

from langgraph.prebuilt import ToolNode

from tradingagents.llm_clients import create_llm_client

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.config import set_config

# Import the new abstract tool methods from agent_utils
from tradingagents.agents.utils.agent_utils import (
    get_stock_data,
    get_indicators,
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_news,
    get_insider_transactions,
    get_global_news
)

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor

logger = logging.getLogger(__name__)


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
        callbacks: Optional[List] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            callbacks: Optional list of callback handlers (e.g., for tracking LLM/tool stats)
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # --- Phase 1: Langfuse observability ---
        self._init_langfuse()

        # --- Phase 1: Model routing ---
        self._model_routing = None
        if self.config.get("model_routing_enabled"):
            self._init_model_routing()

        # Initialize LLMs with provider-specific thinking configuration
        llm_kwargs = self._get_provider_kwargs()

        # Add callbacks to kwargs if provided (passed to LLM constructor)
        if self.callbacks:
            llm_kwargs["callbacks"] = self.callbacks

        if self._model_routing:
            # Per-role model creation via model routing
            self.deep_thinking_llm = self._create_routed_llm("judge", llm_kwargs)
            self.quick_thinking_llm = self._create_routed_llm("data_analyst", llm_kwargs)
        else:
            # Legacy: global 2-layer model
            deep_client = create_llm_client(
                provider=self.config["llm_provider"],
                model=self.config["deep_think_llm"],
                base_url=self.config.get("backend_url"),
                **llm_kwargs,
            )
            quick_client = create_llm_client(
                provider=self.config["llm_provider"],
                model=self.config["quick_think_llm"],
                base_url=self.config.get("backend_url"),
                **llm_kwargs,
            )
            self.deep_thinking_llm = deep_client.get_llm()
            self.quick_thinking_llm = quick_client.get_llm()
        
        # Initialize memories
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
            checkpointer=self.checkpointer,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # --- Phase 1: Database ---
        self.db = None
        if self.config.get("database_enabled"):
            self._init_database()

        # --- Phase 0: LangGraph Checkpointing ---
        self.checkpointer = None
        if self.config.get("checkpointing_enabled"):
            self._init_checkpointer()

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)

    # ------------------------------------------------------------------
    # Phase 1 initializers
    # ------------------------------------------------------------------

    def _init_langfuse(self):
        """Auto-initialize Langfuse callback if configured."""
        if not self.config.get("langfuse_enabled"):
            return
        try:
            from tradingagents.observability import create_langfuse_handler
            handler = create_langfuse_handler(self.config)
            if handler:
                self.callbacks.append(handler)
                logger.info("Langfuse callback handler attached.")
        except Exception as exc:
            logger.warning("Failed to init Langfuse: %s", exc)

    def _init_model_routing(self):
        """Load model routing config from YAML."""
        try:
            from tradingagents.config import load_model_routing
            self._model_routing = load_model_routing(
                config_path=self.config.get("model_routing_config"),
                active_profile=self.config.get("model_routing_profile"),
            )
            logger.info(
                "Model routing enabled — profile: %s",
                self._model_routing.active_profile,
            )
        except Exception as exc:
            logger.warning("Model routing init failed, falling back to legacy: %s", exc)
            self._model_routing = None

    def _init_database(self):
        """Initialize the SQLite database manager."""
        try:
            from tradingagents.database import DatabaseManager
            db_path = self.config.get("database_path", "tradingagents.db")
            self.db = DatabaseManager(db_path)
            logger.info("Database initialized at %s", db_path)
        except Exception as exc:
            logger.warning("Database init failed: %s", exc)
            self.db = None

    def _init_checkpointer(self):
        """Initialize LangGraph checkpointer based on config."""
        try:
            storage = self.config.get("checkpoint_storage", "memory")
            if storage == "memory":
                from langgraph.checkpoint.memory import MemorySaver
                self.checkpointer = MemorySaver()
                logger.info("LangGraph MemorySaver checkpointer initialized.")
            elif storage == "sqlite":
                from langgraph.checkpoint.sqlite import SqliteSaver
                db_path = self.config.get("checkpoint_db_path", "checkpoints.db")
                self.checkpointer = SqliteSaver.from_conn_string(db_path)
                logger.info("LangGraph SQLite checkpointer at %s", db_path)
            else:
                logger.warning("Unknown checkpoint_storage: %s", storage)
        except ImportError as exc:
            logger.warning(
                "Checkpointer init failed (missing package?): %s. "
                "For sqlite storage, install langgraph-checkpoint-sqlite.", exc
            )
            self.checkpointer = None
        except Exception as exc:
            logger.warning("Checkpointer init failed: %s", exc)
            self.checkpointer = None

    def _create_routed_llm(self, role_type: str, llm_kwargs: dict):
        """Create an LLM instance via model routing config."""
        model_name = self._model_routing.get_model(role_type)
        provider = self.config.get("llm_provider", "openai")
        # When model routing is active with litellm, use litellm provider
        if self.config.get("llm_provider") == "litellm":
            provider = "litellm"
        client = create_llm_client(
            provider=provider,
            model=model_name,
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )
        return client.get_llm()

    # ------------------------------------------------------------------
    # Existing methods (unchanged logic)
    # ------------------------------------------------------------------

    def _get_provider_kwargs(self) -> Dict[str, Any]:
        """Get provider-specific kwargs for LLM client creation."""
        kwargs = {}
        provider = self.config.get("llm_provider", "").lower()

        if provider == "google":
            thinking_level = self.config.get("google_thinking_level")
            if thinking_level:
                kwargs["thinking_level"] = thinking_level

        elif provider == "openai":
            reasoning_effort = self.config.get("openai_reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

        return kwargs

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources using abstract methods."""
        return {
            "market": ToolNode(
                [
                    # Core stock data tools
                    get_stock_data,
                    # Technical indicators
                    get_indicators,
                ]
            ),
            "social": ToolNode(
                [
                    # News tools for social media analysis
                    get_news,
                ]
            ),
            "news": ToolNode(
                [
                    # News and insider information
                    get_news,
                    get_global_news,
                    get_insider_transactions,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # Fundamental analysis tools
                    get_fundamentals,
                    get_balance_sheet,
                    get_cashflow,
                    get_income_statement,
                ]
            ),
        }

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )

        # Generate thread_id for checkpointing (only when enabled)
        thread_id = None
        if self.checkpointer is not None:
            thread_id = f"{company_name}-{trade_date}"

        args = self.propagator.get_graph_args(thread_id=thread_id)

        if self.debug:
            # Debug mode with tracing
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if len(chunk["messages"]) == 0:
                    pass
                else:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)

            final_state = trace[-1]
        else:
            # Standard mode without tracing
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        signal = self.process_signal(final_state["final_trade_decision"])

        # --- Phase 1: Persist decision to database ---
        if self.db:
            self._persist_decision(final_state, signal)

        # Return decision and processed signal
        return final_state, signal

    def _persist_decision(self, final_state: dict, signal: str):
        """Save the decision and related data to the database."""
        try:
            # Extract Langfuse trace_id if available
            trace_id = trace_url = None
            if self.config.get("langfuse_enabled") and self.callbacks:
                for cb in self.callbacks:
                    if hasattr(cb, "trace_id") and cb.trace_id:
                        trace_id = cb.trace_id
                        host = self.config.get("langfuse_host", "http://localhost:3000")
                        trace_url = f"{host}/trace/{trace_id}"
                        break

            decision_id = self.db.save_decision({
                "ticker": final_state.get("company_of_interest", self.ticker),
                "trade_date": final_state.get("trade_date", ""),
                "final_decision": signal,
                "langfuse_trace_id": trace_id,
                "langfuse_trace_url": trace_url,
                "market_report": final_state.get("market_report", ""),
                "sentiment_report": final_state.get("sentiment_report", ""),
                "news_report": final_state.get("news_report", ""),
                "fundamentals_report": final_state.get("fundamentals_report", ""),
                "debate_history": final_state.get("investment_debate_state", {}).get("history", ""),
                "risk_assessment": final_state.get("risk_debate_state", {}).get("history", ""),
            })
            logger.info("Decision persisted: id=%d signal=%s trace_id=%s", decision_id, signal, trace_id)
        except Exception as exc:
            logger.warning("Failed to persist decision: %s", exc)

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "aggressive_history": final_state["risk_debate_state"]["aggressive_history"],
                "conservative_history": final_state["risk_debate_state"]["conservative_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
