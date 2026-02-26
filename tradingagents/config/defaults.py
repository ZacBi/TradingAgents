"""Default configuration dict for TradingAgents. Single source of defaults."""

import os
from pathlib import Path

# Package root (tradingagents/)
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CONFIG = {
    "project_dir": str(_PACKAGE_ROOT),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "eval_log_dir": os.getenv("TRADINGAGENTS_EVAL_LOG_DIR", "eval_results"),
    "alpha_vantage_base_url": "https://www.alphavantage.co/query",
    "litellm_base_url": os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    "data_cache_dir": str(_PACKAGE_ROOT / "dataflows" / "data_cache"),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    "google_thinking_level": None,
    "openai_reasoning_effort": None,
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
        "valuation_data": "yfinance",
        "macro_data": "fred",
        "realtime_data": "longport",
    },
    "tool_vendors": {},
    # Model routing
    "model_routing_enabled": False,
    "model_routing_config": None,
    "model_routing_profile": None,
    # Observability (Langfuse)
    "langfuse_enabled": False,
    "langfuse_public_key": None,
    "langfuse_secret_key": None,
    "langfuse_host": "http://localhost:3000",
    # Database (SQLite)
    "database_enabled": True,
    "database_path": "tradingagents.db",
    # LangGraph Checkpointing
    "checkpointing_enabled": True,
    "checkpoint_storage": "memory",
    "checkpoint_db_path": "checkpoints.db",
    "checkpoint_postgres_url": None,
    # Data source API keys
    "fred_api_key": None,
    "longport_app_key": None,
    "longport_app_secret": None,
    "longport_access_token": None,
    # Expert Framework
    "experts_enabled": True,
    "max_experts": 3,
    "expert_selection_mode": "auto",
    "selected_experts": None,
    # Embedding (convergence)
    "embedding_provider": "sentence_transformers",
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    # Dynamic Convergence Detection
    "debate_convergence_enabled": True,
    "debate_semantic_threshold": 0.85,
    "debate_info_gain_threshold": 0.1,
    # Deep Research
    "deep_research_enabled": False,
    "deep_research_provider": "gemini",
    "deep_research_model": "gemini-2.0-flash",
    "deep_research_triggers": ["first_analysis", "pre_earnings"],
    "force_deep_research": False,
    # Earnings Tracking
    "earnings_tracking_enabled": True,
    "earnings_lookahead_days": 14,
    "earnings_imminent_days": 3,
    # Prompt Management (Langfuse)
    "prompt_management_enabled": True,
    "prompt_cache_ttl": 300,
    "prompt_fallback_enabled": True,
    "prompt_version": None,
    # Value Investing (Valuation)
    "valuation_enabled": True,
    "valuation_dcf_projection_years": 5,
    "valuation_terminal_growth_rate": 0.025,
    "valuation_risk_free_rate": 0.04,
    "valuation_market_risk_premium": 0.06,
    "valuation_graham_safety_threshold": 0.30,
    # LangGraph Store (Memory)
    "store_enabled": True,
    "store_backend": "memory",
    "store_postgres_url": None,
    "store_embedding_provider": "openai",
    "store_embedding_model": "text-embedding-3-small",
    "store_embedding_dimension": 1536,
    # PostgreSQL unified
    "postgres_url": None,
}
