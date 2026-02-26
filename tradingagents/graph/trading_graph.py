# TradingAgents/graph/trading_graph.py

import json
import logging
import os
from pathlib import Path
from typing import Any

from langgraph.prebuilt import ToolNode

# Import tool methods directly from their modules
from tradingagents.agents.utils.core_stock_tools import get_stock_data
from tradingagents.agents.utils.fundamental_data_tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from tradingagents.agents.utils.macro_data_tools import (
    get_cpi_data,
    get_gdp_data,
    get_interest_rate_data,
    get_m2_data,
    get_unemployment_data,
)
from tradingagents.agents.utils.news_data_tools import (
    get_global_news,
    get_insider_transactions,
    get_news,
)
from tradingagents.agents.utils.realtime_data_tools import (
    get_kline_data,
    get_realtime_quote,
)
from tradingagents.agents.utils.technical_indicators_tools import get_indicators
from tradingagents.agents.utils.valuation_data_tools import (
    get_earnings_dates,
    get_institutional_holders,
    get_valuation_metrics,
)
from tradingagents.agents.utils.memory import (
    FinancialSituationMemory,
    create_embedder,
    create_memory_store,
)
from tradingagents.config import DEFAULT_CONFIG, set_config
from tradingagents.llm_clients import create_llm_client

from .conditional_logic import ConditionalLogic
from .error_recovery import ErrorRecovery
from .propagation import Propagator
from .recovery import RecoveryEngine
from .reflection import Reflector
from .setup import GraphSetup
from .signal_processing import SignalProcessor

logger = logging.getLogger(__name__)


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=None,
        debug=False,
        config: dict[str, Any] = None,
        callbacks: list | None = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            callbacks: Optional list of callback handlers (e.g., for tracking LLM/tool stats)
        """
        if selected_analysts is None:
            selected_analysts = ["market", "social", "news", "fundamentals"]
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

        # --- Prompt Management (Langfuse) ---
        self.prompt_manager = None
        if self.config.get("prompt_management_enabled", True):
            self._init_prompt_manager()

        # --- Phase 1: Model routing ---
        self._model_routing = None
        if self.config.get("model_routing_enabled"):
            self._init_model_routing()

        # Initialize LLMs with provider-specific thinking configuration
        llm_kwargs = self._get_provider_kwargs()

        # Add callbacks to kwargs if provided (passed to LLM constructor)
        if self.callbacks:
            llm_kwargs["callbacks"] = self.callbacks

        # Optional overrides for testing (e.g. FakeListChatModel in E2E)
        if self.config.get("quick_think_llm_override") is not None:
            self.quick_thinking_llm = self.config["quick_think_llm_override"]
            self.deep_thinking_llm = self.config.get("deep_think_llm_override") or self.quick_thinking_llm
        elif self._model_routing:
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

        # --- Phase 5: Initialize LangGraph Store for memory ---
        self.store = None
        self.embedder = None
        if self.config.get("store_enabled", True):
            self._init_store()

        # Initialize memories with store and embedder
        self.bull_memory = FinancialSituationMemory("bull", self.store, self.embedder)
        self.bear_memory = FinancialSituationMemory("bear", self.store, self.embedder)
        self.trader_memory = FinancialSituationMemory("trader", self.store, self.embedder)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge", self.store, self.embedder)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager", self.store, self.embedder)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # --- Phase 0: LangGraph Checkpointing (before GraphSetup) ---
        self.checkpointer = None
        self.recovery_engine = None
        if self.config.get("checkpointing_enabled"):
            self._init_checkpointer()
            if self.checkpointer:
                self.recovery_engine = RecoveryEngine(self.checkpointer)

        # Initialize components
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config.get("max_debate_rounds", 1),
            max_risk_discuss_rounds=self.config.get("max_risk_discuss_rounds", 1),
            config=self.config,  # Pass full config for convergence detection
        )
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
            config=self.config,
            prompt_manager=self.prompt_manager,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)
        
        # Phase 4: Error recovery
        self.error_recovery = ErrorRecovery(self.config.get("error_recovery_config", {}))

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # --- Phase 1: Database ---
        self.db = None
        if self.config.get("database_enabled"):
            self._init_database()
        
        # --- Phase 3: Trading Interface ---
        self.trading_interface = None
        self.risk_controller = None
        self.order_executor = None
        self.order_manager = None
        self.position_manager = None
        if self.config.get("trading_enabled", False):
            self._init_trading()
        
        # Pass order_executor to graph_setup BEFORE setting up graph
        if self.order_executor:
            self.graph_setup.order_executor = self.order_executor

        # Phase 4: Apply workflow configuration if provided
        if self.config.get("workflow_config_file"):
            from tradingagents.config.workflow_config import WorkflowConfig, WorkflowBuilder
            workflow_config = WorkflowConfig.from_file(self.config["workflow_config_file"])
            workflow_builder = WorkflowBuilder(workflow_config)
            workflow_builder.apply_to_graph_setup(self.graph_setup)
            # Use configured analysts
            selected_analysts = workflow_config.get_analysts()
        
        # Phase 4: Load plugins if enabled
        if self.config.get("plugins_enabled", False):
            from tradingagents.plugins import PluginManager
            plugin_dirs = self.config.get("plugin_dirs", [])
            plugin_manager = PluginManager(plugin_dirs=plugin_dirs)
            plugin_manager.discover_and_load_plugins()
            # Register plugins with node factory
            if hasattr(self.graph_setup, "node_factory"):
                self.graph_setup.node_factory.set_plugin_manager(plugin_manager)
        
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

    def _init_prompt_manager(self):
        """Initialize the Langfuse prompt manager."""
        try:
            from tradingagents.prompts import PromptManager
            self.prompt_manager = PromptManager(self.config)
            if self.prompt_manager.is_available():
                logger.info("Langfuse prompt management enabled.")
            else:
                logger.info("Prompt management using local fallback templates.")
        except Exception as exc:
            logger.warning("Failed to init PromptManager: %s", exc)
            self.prompt_manager = None

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

    def _init_store(self):
        """Initialize LangGraph Store for semantic memory retrieval."""
        try:
            self.store = create_memory_store(self.config)
            if self.store:
                self.embedder = create_embedder(self.config)
                logger.info("LangGraph Store initialized with embedder.")
            else:
                logger.info("LangGraph Store disabled or failed to initialize.")
        except Exception as exc:
            logger.warning("Store init failed: %s", exc)
            self.store = None
            self.embedder = None

    def _init_checkpointer(self):
        """Initialize LangGraph checkpointer based on config.
        
        Follows LangGraph best practices (2025):
        - For PostgreSQL: calls .setup() to create tables
        - Uses connection pooling for better performance
        - Handles async operations properly
        """
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
            elif storage == "postgres":
                from langgraph.checkpoint.postgres import PostgresSaver
                pg_url = self.config.get("postgres_url") or self.config.get("checkpoint_postgres_url")
                if not pg_url:
                    logger.error("PostgreSQL URL not configured for checkpointer.")
                    self.checkpointer = None
                    return
                
                # Create PostgresSaver with connection string
                self.checkpointer = PostgresSaver.from_conn_string(pg_url)
                
                # Best practice: Call .setup() to create required tables
                # This is required for first-time setup
                try:
                    self.checkpointer.setup()
                    logger.info("LangGraph PostgresSaver checkpointer initialized and tables created.")
                except Exception as setup_exc:
                    # Tables might already exist, which is fine
                    if "already exists" in str(setup_exc).lower() or "duplicate" in str(setup_exc).lower():
                        logger.info("LangGraph PostgresSaver checkpointer initialized (tables already exist).")
                    else:
                        logger.warning("PostgresSaver.setup() failed (non-critical): %s", setup_exc)
                        # Continue anyway - tables might already exist
                
                logger.info("LangGraph PostgresSaver checkpointer ready for use.")
            else:
                logger.warning("Unknown checkpoint_storage: %s", storage)
        except ImportError as exc:
            logger.warning(
                "Checkpointer init failed (missing package?): %s. "
                "For postgres storage, install: pip install psycopg psycopg-pool langgraph-checkpoint-postgres", exc
            )
            self.checkpointer = None
        except Exception as exc:
            logger.warning("Checkpointer init failed: %s", exc)
            self.checkpointer = None
    
    def _init_trading(self):
        """Initialize trading interface and related components."""
        try:
            from tradingagents.trading import AlpacaAdapter, OrderManager, PositionManager
            from tradingagents.trading.risk_controller import RiskController
            from tradingagents.trading.order_executor import OrderExecutor
            
            # Initialize trading interface
            trading_config = {
                "api_key": self.config.get("alpaca_api_key"),
                "api_secret": self.config.get("alpaca_api_secret"),
                "paper": self.config.get("alpaca_paper", True),
                "base_url": self.config.get("alpaca_base_url"),
            }
            
            self.trading_interface = AlpacaAdapter(trading_config)
            if not self.trading_interface.connect():
                logger.warning("Failed to connect to trading interface")
                self.trading_interface = None
                return
            
            # Initialize risk controller
            risk_config = self.config.get("risk_config", {})
            self.risk_controller = RiskController(risk_config)
            
            # Initialize order executor (pass LLM for structured output parsing)
            self.order_executor = OrderExecutor(
                trading_interface=self.trading_interface,
                risk_controller=self.risk_controller,
                llm=self.quick_thinking_llm,  # Use quick thinking LLM for parsing
            )
            
            # Initialize managers
            self.order_manager = OrderManager(self.trading_interface)
            self.position_manager = PositionManager(self.trading_interface)
            
            logger.info("Trading interface initialized")
        except ImportError as exc:
            logger.warning(
                "Trading init failed (missing packages?): %s. "
                "For trading, install: pip install alpaca-py skfolio", exc
            )
            self.trading_interface = None
        except Exception as exc:
            logger.warning("Trading init failed: %s", exc)
            self.trading_interface = None

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

    def _get_provider_kwargs(self) -> dict[str, Any]:
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

    def _create_tool_nodes(self) -> dict[str, ToolNode]:
        """Create tool nodes for different data sources using abstract methods."""
        return {
            "market": ToolNode(
                [
                    # Core stock data tools
                    get_stock_data,
                    # Technical indicators
                    get_indicators,
                    # Real-time data tools (Phase 2)
                    get_realtime_quote,
                    get_kline_data,
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
                    # Macroeconomic data tools (Phase 2)
                    get_cpi_data,
                    get_gdp_data,
                    get_interest_rate_data,
                    get_unemployment_data,
                    get_m2_data,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # Fundamental analysis tools
                    get_fundamentals,
                    get_balance_sheet,
                    get_cashflow,
                    get_income_statement,
                    # Valuation data tools (Phase 2)
                    get_earnings_dates,
                    get_valuation_metrics,
                    get_institutional_holders,
                ]
            ),
        }

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""
        from tradingagents.utils.validation import validate_ticker, validate_trade_date

        validate_ticker(company_name)
        validate_trade_date(trade_date)

        self.ticker = company_name

        # Lineage: collect data_ids during this run for decision_data_links
        from tradingagents.graph.lineage import get_data_ids, set_lineage_collector
        set_lineage_collector([])
        if self.config.get("database_enabled") and self.db:
            from tradingagents.config import set_config
            set_config({**self.config, "db": self.db})

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )

        # Generate thread_id for checkpointing (only when enabled)
        thread_id = None
        if self.checkpointer is not None:
            thread_id = f"{company_name}-{trade_date}"
            
            # Phase 2: Try to recover state if available
            if self.recovery_engine and self.recovery_engine.can_recover(thread_id):
                logger.info("Recovering state from checkpoint for thread_id: %s", thread_id)
                recovered_state = self.recovery_engine.recover_state(thread_id, merge_with_initial=init_agent_state)
                if recovered_state:
                    # Use merged state
                    init_agent_state = recovered_state
                    logger.info("State recovered and merged successfully")

        args = self.propagator.get_graph_args(thread_id=thread_id)

        # Phase 4: Execute with error recovery
        if self.debug:
            # Debug mode with tracing
            trace = []
            def stream_graph():
                for chunk in self.graph.stream(init_agent_state, **args):
                    if len(chunk["messages"]) == 0:
                        pass
                    else:
                        chunk["messages"][-1].pretty_print()
                        trace.append(chunk)
                return trace[-1] if trace else init_agent_state
            
            final_state, error = self.error_recovery.execute_with_retry(stream_graph)
            if error:
                logger.error("Graph execution failed after retries: %s", error)
                # Return partial state if available
                final_state = trace[-1] if trace else init_agent_state
        else:
            # Standard mode without tracing
            def invoke_graph():
                return self.graph.invoke(init_agent_state, **args)
            
            final_state, error = self.error_recovery.execute_with_retry(invoke_graph)
            if error:
                logger.error("Graph execution failed after retries: %s", error)
                # Return initial state as fallback
                final_state = init_agent_state

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        signal = self.process_signal(final_state["final_trade_decision"])

        # --- Phase 1: Persist decision to database ---
        data_ids = get_data_ids()
        if self.db:
            self._persist_decision(final_state, signal, data_ids=data_ids)

        # Return decision and processed signal
        return final_state, signal

    def persist_decision(self, final_state: dict, signal: str) -> None:
        """Persist a decision to the database (if database_enabled).
        Call this from CLI or other entry points that run the graph without propagate().
        """
        if self.db:
            from tradingagents.graph.lineage import get_data_ids
            self._persist_decision(final_state, signal, data_ids=get_data_ids())

    def _persist_decision(
        self,
        final_state: dict,
        signal: str,
        data_ids: list[tuple] | None = None,
    ):
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
                "valuation_result": final_state.get("valuation_result", ""),
                "debate_history": final_state.get("investment_debate_state", {}).get("history", ""),
                "risk_assessment": final_state.get("risk_debate_state", {}).get("history", ""),
            })
            # Link raw data used in this run to the decision
            for data_type, raw_id in (data_ids or []):
                try:
                    self.db.link_data_to_decision(decision_id, data_type, raw_id)
                except Exception as link_exc:
                    logger.warning("Failed to link data to decision: %s", link_exc)
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
            "valuation_result": final_state.get("valuation_result", ""),
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
        log_dir = self.config.get("eval_log_dir", "eval_results")
        directory = Path(log_dir) / self.ticker / "TradingAgentsStrategy_logs"
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            directory / f"full_states_log_{trade_date}.json",
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
