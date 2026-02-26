"""Plugin system for TradingAgents.

Provides dynamic loading and registration of agent plugins.
"""

from .manager import PluginManager
from .registry import PluginRegistry

__all__ = ["PluginManager", "PluginRegistry"]
