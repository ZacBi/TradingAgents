"""Pydantic Settings v2 configuration system for TradingAgents.

Provides type-safe, validated configuration with environment variable support.
Replaces dict-based DEFAULT_CONFIG with structured Pydantic models.

Usage:
    from tradingagents.config.settings import get_settings

    settings = get_settings()
    print(settings.llm_provider)
    print(settings.database.path)

    # For backward compatibility with dict access:
    config_dict = settings.to_dict()
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Keys masked in to_dict(safe=True) to avoid leaking into logs/APIs
_SECRET_CONFIG_KEYS = frozenset({
    "fred_api_key", "longport_app_key", "longport_app_secret",
    "longport_access_token", "langfuse_secret_key", "langfuse_public_key",
})


class LLMSettings(BaseSettings):
    """LLM provider and model configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_LLM_",
        extra="ignore",
    )

    provider: Literal["openai", "google", "anthropic", "litellm"] = "openai"
    deep_think_llm: str = "gpt-5.2"
    quick_think_llm: str = "gpt-5-mini"
    backend_url: str = "https://api.openai.com/v1"

    # Provider-specific thinking configuration
    google_thinking_level: str | None = None
    openai_reasoning_effort: str | None = None


class DataVendorSettings(BaseSettings):
    """Data source vendor configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_VENDOR_",
        extra="ignore",
    )

    core_stock_apis: Literal["yfinance", "alpha_vantage"] = "yfinance"
    technical_indicators: Literal["yfinance", "alpha_vantage", "local"] = "yfinance"
    fundamental_data: Literal["yfinance", "alpha_vantage"] = "yfinance"
    news_data: Literal["yfinance", "alpha_vantage"] = "yfinance"
    valuation_data: Literal["yfinance"] = "yfinance"
    macro_data: Literal["fred"] = "fred"
    realtime_data: Literal["longport"] = "longport"


class DatabaseSettings(BaseSettings):
    """Database configuration (SQLAlchemy + Alembic)."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_DB_",
        extra="ignore",
    )

    enabled: bool = True
    path: str = "tradingagents.db"
    url: str | None = Field(
        default=None,
        description="Full database URL. If set, overrides path for SQLite.",
    )

    @property
    def connection_url(self) -> str:
        """Get the full database connection URL."""
        if self.url:
            return self.url
        return f"sqlite:///{self.path}"


class CheckpointSettings(BaseSettings):
    """LangGraph checkpoint persistence configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_CHECKPOINT_",
        extra="ignore",
    )

    enabled: bool = True
    storage: Literal["memory", "sqlite", "postgres"] = "memory"
    sqlite_path: str = "checkpoints.db"
    postgres_url: str | None = Field(
        default=None,
        validation_alias="TRADINGAGENTS_POSTGRES_URL",
    )


class StoreSettings(BaseSettings):
    """LangGraph Store (memory system) configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_STORE_",
        extra="ignore",
    )

    enabled: bool = True
    backend: Literal["memory", "postgres"] = "memory"
    postgres_url: str | None = Field(
        default=None,
        validation_alias="TRADINGAGENTS_POSTGRES_URL",
    )

    # Embedding configuration for semantic search
    embedding_provider: Literal["openai", "sentence_transformers"] = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536


class LangfuseSettings(BaseSettings):
    """Langfuse observability configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LANGFUSE_",
        extra="ignore",
    )

    enabled: bool = Field(default=False, validation_alias="TRADINGAGENTS_LANGFUSE_ENABLED")
    public_key: str | None = Field(default=None, validation_alias="LANGFUSE_PUBLIC_KEY")
    secret_key: str | None = Field(default=None, validation_alias="LANGFUSE_SECRET_KEY")
    host: str = "http://localhost:3000"


class DebateSettings(BaseSettings):
    """Agent debate and discussion configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_DEBATE_",
        extra="ignore",
    )

    max_rounds: int = 1
    max_risk_discuss_rounds: int = 1
    max_recur_limit: int = 100

    # Dynamic convergence detection
    convergence_enabled: bool = True
    semantic_threshold: float = 0.85
    info_gain_threshold: float = 0.1


class ExpertsSettings(BaseSettings):
    """Expert framework configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_EXPERT_",
        extra="ignore",
    )

    enabled: bool = True
    max_experts: int = 3
    selection_mode: Literal["auto", "manual", "random"] = "auto"
    selected_experts: list[str] | None = None


class DeepResearchSettings(BaseSettings):
    """Deep research configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_RESEARCH_",
        extra="ignore",
    )

    enabled: bool = False
    provider: Literal["gemini", "openai"] = "gemini"
    model: str = "gemini-2.0-flash"
    triggers: list[str] = ["first_analysis", "pre_earnings"]
    force: bool = False


class ValuationSettings(BaseSettings):
    """Value investing framework configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_VALUATION_",
        extra="ignore",
    )

    enabled: bool = True
    dcf_projection_years: int = 5
    terminal_growth_rate: float = 0.025
    risk_free_rate: float = 0.04
    market_risk_premium: float = 0.06
    graham_safety_threshold: float = 0.30


class EarningsSettings(BaseSettings):
    """Earnings tracking configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_EARNINGS_",
        extra="ignore",
    )

    tracking_enabled: bool = True
    lookahead_days: int = 14
    imminent_days: int = 3


class PromptSettings(BaseSettings):
    """Prompt management configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADINGAGENTS_PROMPT_",
        extra="ignore",
    )

    management_enabled: bool = True
    cache_ttl: int = 300
    fallback_enabled: bool = True
    version: str | None = None


class APIKeySettings(BaseSettings):
    """External API key configuration."""

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    fred_api_key: str | None = Field(default=None, validation_alias="FRED_API_KEY")
    longport_app_key: str | None = Field(default=None, validation_alias="LONGPORT_APP_KEY")
    longport_app_secret: str | None = Field(default=None, validation_alias="LONGPORT_APP_SECRET")
    longport_access_token: str | None = Field(default=None, validation_alias="LONGPORT_ACCESS_TOKEN")


class Settings(BaseSettings):
    """Root settings class aggregating all configuration sections.

    Environment variables are loaded automatically with the following prefixes:
    - TRADINGAGENTS_* for general settings
    - LANGFUSE_* for observability
    - FRED_API_KEY, LONGPORT_* for API keys

    Example .env file:
        TRADINGAGENTS_LLM_PROVIDER=openai
        TRADINGAGENTS_DB_PATH=my_database.db
        TRADINGAGENTS_POSTGRES_URL=postgresql://user:pass@localhost/tradingagents
        LANGFUSE_PUBLIC_KEY=pk-xxx
        FRED_API_KEY=xxx
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TRADINGAGENTS_",
        extra="ignore",
    )

    # Directory paths
    project_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.resolve()
    )
    results_dir: Path = Field(
        default=Path("./results"),
        validation_alias="TRADINGAGENTS_RESULTS_DIR",
    )
    data_cache_dir: Path | None = None

    # Nested configuration sections
    llm: LLMSettings = Field(default_factory=LLMSettings)
    data_vendors: DataVendorSettings = Field(default_factory=DataVendorSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    checkpoint: CheckpointSettings = Field(default_factory=CheckpointSettings)
    store: StoreSettings = Field(default_factory=StoreSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    debate: DebateSettings = Field(default_factory=DebateSettings)
    experts: ExpertsSettings = Field(default_factory=ExpertsSettings)
    deep_research: DeepResearchSettings = Field(default_factory=DeepResearchSettings)
    valuation: ValuationSettings = Field(default_factory=ValuationSettings)
    earnings: EarningsSettings = Field(default_factory=EarningsSettings)
    prompts: PromptSettings = Field(default_factory=PromptSettings)
    api_keys: APIKeySettings = Field(default_factory=APIKeySettings)

    # Model routing
    model_routing_enabled: bool = False
    model_routing_config: str | None = None
    model_routing_profile: str | None = None

    # Unified PostgreSQL URL (shared across Store, Checkpoint, Database)
    postgres_url: str | None = Field(
        default=None,
        validation_alias="TRADINGAGENTS_POSTGRES_URL",
    )

    # Tool-level vendor overrides
    tool_vendors: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def set_derived_paths(self) -> "Settings":
        """Set derived paths after model initialization."""
        if self.data_cache_dir is None:
            self.data_cache_dir = self.project_dir / "dataflows" / "data_cache"
        return self

    @model_validator(mode="after")
    def propagate_postgres_url(self) -> "Settings":
        """Propagate unified postgres_url to sub-settings if not set."""
        if self.postgres_url:
            if self.store.postgres_url is None:
                self.store.postgres_url = self.postgres_url
            if self.checkpoint.postgres_url is None:
                self.checkpoint.postgres_url = self.postgres_url
            if self.database.url is None and self.postgres_url.startswith("postgresql"):
                self.database.url = self.postgres_url
        return self

    def to_dict(self, safe: bool = True) -> dict:
        """Convert to flat dictionary for backward compatibility.

        Returns a dict matching the original DEFAULT_CONFIG structure.
        When safe=True (default), secret-like keys are masked to avoid leaking into logs/APIs.
        """
        raw = {
            "project_dir": str(self.project_dir),
            "results_dir": str(self.results_dir),
            "data_cache_dir": str(self.data_cache_dir),
            # LLM settings
            "llm_provider": self.llm.provider,
            "deep_think_llm": self.llm.deep_think_llm,
            "quick_think_llm": self.llm.quick_think_llm,
            "backend_url": self.llm.backend_url,
            "google_thinking_level": self.llm.google_thinking_level,
            "openai_reasoning_effort": self.llm.openai_reasoning_effort,
            # Debate settings
            "max_debate_rounds": self.debate.max_rounds,
            "max_risk_discuss_rounds": self.debate.max_risk_discuss_rounds,
            "max_recur_limit": self.debate.max_recur_limit,
            # Data vendors
            "data_vendors": {
                "core_stock_apis": self.data_vendors.core_stock_apis,
                "technical_indicators": self.data_vendors.technical_indicators,
                "fundamental_data": self.data_vendors.fundamental_data,
                "news_data": self.data_vendors.news_data,
                "valuation_data": self.data_vendors.valuation_data,
                "macro_data": self.data_vendors.macro_data,
                "realtime_data": self.data_vendors.realtime_data,
            },
            "tool_vendors": self.tool_vendors,
            # Model routing
            "model_routing_enabled": self.model_routing_enabled,
            "model_routing_config": self.model_routing_config,
            "model_routing_profile": self.model_routing_profile,
            # Langfuse
            "langfuse_enabled": self.langfuse.enabled,
            "langfuse_public_key": self.langfuse.public_key,
            "langfuse_secret_key": self.langfuse.secret_key,
            "langfuse_host": self.langfuse.host,
            # Database
            "database_enabled": self.database.enabled,
            "database_path": self.database.path,
            # Checkpoint
            "checkpointing_enabled": self.checkpoint.enabled,
            "checkpoint_storage": self.checkpoint.storage,
            "checkpoint_db_path": self.checkpoint.sqlite_path,
            "checkpoint_postgres_url": self.checkpoint.postgres_url,
            # API keys
            "fred_api_key": self.api_keys.fred_api_key,
            "longport_app_key": self.api_keys.longport_app_key,
            "longport_app_secret": self.api_keys.longport_app_secret,
            "longport_access_token": self.api_keys.longport_access_token,
            # Experts
            "experts_enabled": self.experts.enabled,
            "max_experts": self.experts.max_experts,
            "expert_selection_mode": self.experts.selection_mode,
            "selected_experts": self.experts.selected_experts,
            # Embedding (for convergence detection)
            "embedding_provider": self.store.embedding_provider,
            "embedding_model": self.store.embedding_model,
            "embedding_dimension": self.store.embedding_dimension,
            # Convergence
            "debate_convergence_enabled": self.debate.convergence_enabled,
            "debate_semantic_threshold": self.debate.semantic_threshold,
            "debate_info_gain_threshold": self.debate.info_gain_threshold,
            # Deep research
            "deep_research_enabled": self.deep_research.enabled,
            "deep_research_provider": self.deep_research.provider,
            "deep_research_model": self.deep_research.model,
            "deep_research_triggers": self.deep_research.triggers,
            "force_deep_research": self.deep_research.force,
            # Earnings
            "earnings_tracking_enabled": self.earnings.tracking_enabled,
            "earnings_lookahead_days": self.earnings.lookahead_days,
            "earnings_imminent_days": self.earnings.imminent_days,
            # Prompts
            "prompt_management_enabled": self.prompts.management_enabled,
            "prompt_cache_ttl": self.prompts.cache_ttl,
            "prompt_fallback_enabled": self.prompts.fallback_enabled,
            "prompt_version": self.prompts.version,
            # Valuation
            "valuation_enabled": self.valuation.enabled,
            "valuation_dcf_projection_years": self.valuation.dcf_projection_years,
            "valuation_terminal_growth_rate": self.valuation.terminal_growth_rate,
            "valuation_risk_free_rate": self.valuation.risk_free_rate,
            "valuation_market_risk_premium": self.valuation.market_risk_premium,
            "valuation_graham_safety_threshold": self.valuation.graham_safety_threshold,
            # Store
            "store_enabled": self.store.enabled,
            "store_backend": self.store.backend,
            "store_postgres_url": self.store.postgres_url,
            "store_embedding_provider": self.store.embedding_provider,
            "store_embedding_model": self.store.embedding_model,
            "store_embedding_dimension": self.store.embedding_dimension,
            # Unified postgres
            "postgres_url": self.postgres_url,
        }
        if safe:
            for k in _SECRET_CONFIG_KEYS:
                if k in raw and raw[k] is not None and raw[k] != "":
                    raw[k] = "***"
        return raw


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses LRU cache for singleton pattern. Call get_settings.cache_clear()
    to reload settings from environment.
    """
    return Settings()


def get_config() -> dict:
    """Return env-based config as dict (sanitized: secrets masked).
    For runtime graph config use get_config from this package (tradingagents.config).
    """
    return get_settings().to_dict(safe=True)
