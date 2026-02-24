import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
    # ----- Phase 1: Model routing -----
    # When enabled, per-role model selection from model_routing.yaml is used
    # instead of the global deep_think_llm / quick_think_llm pair.
    "model_routing_enabled": False,
    "model_routing_config": None,       # Path to model_routing.yaml (auto-detected if None)
    "model_routing_profile": None,      # Override active_profile from YAML
    # ----- Phase 1: Observability (Langfuse) -----
    "langfuse_enabled": False,
    "langfuse_public_key": None,        # or set LANGFUSE_PUBLIC_KEY env var
    "langfuse_secret_key": None,        # or set LANGFUSE_SECRET_KEY env var
    "langfuse_host": "http://localhost:3000",
    # ----- Phase 1: Database (SQLite) -----
    "database_enabled": True,
    "database_path": "tradingagents.db",
    # ----- Phase 0: LangGraph Checkpointing -----
    "checkpointing_enabled": True,
    "checkpoint_storage": "memory",        # memory | sqlite (sqlite requires langgraph-checkpoint-sqlite)
    "checkpoint_db_path": "checkpoints.db",
}
