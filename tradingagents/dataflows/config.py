
import tradingagents.default_config as default_config

# Use default config but allow it to be overridden
_config: dict | None = None


def initialize_config():
    """Initialize the configuration with default values."""
    global _config
    if _config is None:
        _config = default_config.DEFAULT_CONFIG.copy()


def set_config(config: dict):
    """Update the configuration with custom values."""
    global _config
    if _config is None:
        _config = default_config.DEFAULT_CONFIG.copy()
    _config.update(config)


def get_config() -> dict:
    """Get the current runtime configuration (set by graph/CLI via set_config).
    For env-based config with masked secrets, use tradingagents.config.get_config().
    """
    if _config is None:
        initialize_config()
    return _config.copy()


# Initialize with default config
initialize_config()
