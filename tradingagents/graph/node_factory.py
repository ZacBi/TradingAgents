"""Node Factory for TradingAgents graph.

Provides unified interface for creating agent nodes, supporting dynamic registration.
"""

import logging
from typing import Any, Callable

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


class NodeFactory:
    """Factory for creating agent nodes.
    
    Supports dynamic registration of new agent types.
    """
    
    def __init__(self, quick_thinking_llm, deep_thinking_llm, memories: dict, tool_nodes: dict):
        """Initialize node factory.
        
        Args:
            quick_thinking_llm: LLM for quick thinking tasks
            deep_thinking_llm: LLM for deep thinking tasks
            memories: Dictionary of memory instances
            tool_nodes: Dictionary of tool nodes
        """
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.memories = memories
        self.tool_nodes = tool_nodes
        self._analyst_creators = {}
        self._core_creators = {}
        self._plugin_manager = None  # Will be set if plugins are enabled
        self._register_default_creators()
    
    def _register_default_creators(self):
        """Register default agent creators."""
        from tradingagents.agents import (
            create_aggressive_debator,
            create_bear_researcher,
            create_bull_researcher,
            create_conservative_debator,
            create_fundamentals_analyst,
            create_market_analyst,
            create_neutral_debator,
            create_news_analyst,
            create_research_manager,
            create_risk_manager,
            create_social_media_analyst,
            create_trader,
        )
        
        # Analyst creators
        self._analyst_creators = {
            "market": (create_market_analyst, "market"),
            "social": (create_social_media_analyst, "social"),
            "news": (create_news_analyst, "news"),
            "fundamentals": (create_fundamentals_analyst, "fundamentals"),
        }
        
        # Core agent creators
        self._core_creators = {
            "bull_researcher": (create_bull_researcher, self.memories.get("bull")),
            "bear_researcher": (create_bear_researcher, self.memories.get("bear")),
            "research_manager": (create_research_manager, self.memories.get("invest_judge")),
            "trader": (create_trader, self.memories.get("trader")),
            "aggressive_debator": (create_aggressive_debator, None),
            "conservative_debator": (create_conservative_debator, None),
            "neutral_debator": (create_neutral_debator, None),
            "risk_manager": (create_risk_manager, self.memories.get("risk_manager")),
        }
    
    def register_analyst(self, key: str, creator: Callable, tool_key: str):
        """Register a new analyst type.
        
        Args:
            key: Analyst key (e.g., "market")
            creator: Creator function
            tool_key: Tool node key
        """
        self._analyst_creators[key] = (creator, tool_key)
        logger.info(f"Registered analyst: {key}")
    
    def set_plugin_manager(self, plugin_manager):
        """Set plugin manager for dynamic plugin loading.
        
        Args:
            plugin_manager: PluginManager instance
        """
        self._plugin_manager = plugin_manager
        # Load plugins and register them
        if plugin_manager:
            plugin_manager.discover_and_load_plugins()
            # Register plugin-based analysts
            for plugin_info in plugin_manager.list_available_plugins("analyst"):
                plugin_id = plugin_info["plugin_id"]
                instance = plugin_manager.create_plugin_instance(plugin_id)
                if instance and hasattr(instance, "create_analyst"):
                    # Assume plugin provides create_analyst method
                    creator = instance.create_analyst
                    tool_key = plugin_info.get("tool_key", plugin_id)
                    self.register_analyst(plugin_id, creator, tool_key)
    
    def create_analyst_nodes(self, selected_analysts: list) -> tuple[dict, dict]:
        """Create analyst nodes for selected analysts.
        
        Args:
            selected_analysts: List of analyst keys
            
        Returns:
            Tuple of (analyst_nodes_dict, tool_nodes_dict)
        """
        analyst_nodes = {}
        tool_nodes = {}
        
        for key in selected_analysts:
            if key not in self._analyst_creators:
                logger.warning(f"Unknown analyst key: {key}")
                continue
            
            create_fn, tool_key = self._analyst_creators[key]
            analyst_nodes[key] = create_fn(self.quick_thinking_llm)
            tool_nodes[key] = self.tool_nodes[tool_key]
        
        return analyst_nodes, tool_nodes
    
    def create_core_nodes(self) -> dict:
        """Create core agent nodes.
        
        Returns:
            Dictionary of node_name -> node_function
        """
        nodes = {}
        
        # Researchers
        nodes["Bull Researcher"] = self._core_creators["bull_researcher"][0](
            self.quick_thinking_llm, self._core_creators["bull_researcher"][1]
        )
        nodes["Bear Researcher"] = self._core_creators["bear_researcher"][0](
            self.quick_thinking_llm, self._core_creators["bear_researcher"][1]
        )
        
        # Managers
        nodes["Research Manager"] = self._core_creators["research_manager"][0](
            self.deep_thinking_llm, self._core_creators["research_manager"][1]
        )
        nodes["Risk Judge"] = self._core_creators["risk_manager"][0](
            self.deep_thinking_llm, self._core_creators["risk_manager"][1]
        )
        
        # Trader
        nodes["Trader"] = self._core_creators["trader"][0](
            self.quick_thinking_llm, self._core_creators["trader"][1]
        )
        
        # Risk Debators
        nodes["Aggressive Analyst"] = self._core_creators["aggressive_debator"][0](
            self.quick_thinking_llm
        )
        nodes["Conservative Analyst"] = self._core_creators["conservative_debator"][0](
            self.quick_thinking_llm
        )
        nodes["Neutral Analyst"] = self._core_creators["neutral_debator"][0](
            self.quick_thinking_llm
        )
        
        return nodes
