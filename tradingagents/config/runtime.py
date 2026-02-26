"""Runtime configuration (mutable dict) for graph and dataflows. Set by TradingAgentsGraph/CLI."""

from .defaults import DEFAULT_CONFIG

_config: dict | None = None


def initialize_config() -> None:
    """Initialize the configuration with default values."""
    global _config
    if _config is None:
        _config = DEFAULT_CONFIG.copy()


def set_config(config: dict) -> None:
    """Update the configuration with custom values."""
    global _config
    if _config is None:
        _config = DEFAULT_CONFIG.copy()
    _config.update(config)


def get_config() -> dict:
    """Return current runtime config (dict). For env-based config use get_settings().to_dict()."""
    if _config is None:
        initialize_config()
    return _config.copy()


initialize_config()
