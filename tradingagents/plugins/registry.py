"""Plugin Registry for TradingAgents.

Manages plugin registration and discovery.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginMetadata:
    """Metadata for a plugin."""
    
    def __init__(
        self,
        plugin_id: str,
        name: str,
        version: str,
        description: str,
        plugin_type: str,
        entry_point: Any,
        config_schema: Optional[Dict] = None,
    ):
        """Initialize plugin metadata.
        
        Args:
            plugin_id: Unique plugin identifier
            name: Plugin display name
            version: Plugin version
            description: Plugin description
            plugin_type: Type of plugin (agent, data_source, strategy, etc.)
            entry_point: Plugin entry point (class or function)
            config_schema: Optional configuration schema
        """
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.description = description
        self.plugin_type = plugin_type
        self.entry_point = entry_point
        self.config_schema = config_schema or {}


class PluginRegistry:
    """Registry for managing plugins.
    
    Supports dynamic registration and discovery of plugins.
    """
    
    def __init__(self):
        """Initialize plugin registry."""
        self._plugins: Dict[str, PluginMetadata] = {}
        self._plugins_by_type: Dict[str, List[str]] = {}
        self._logger = logging.getLogger(__name__)
    
    def register(
        self,
        plugin_id: str,
        name: str,
        version: str,
        description: str,
        plugin_type: str,
        entry_point: Any,
        config_schema: Optional[Dict] = None,
    ):
        """Register a plugin.
        
        Args:
            plugin_id: Unique plugin identifier
            name: Plugin display name
            version: Plugin version
            description: Plugin description
            plugin_type: Type of plugin
            entry_point: Plugin entry point
            config_schema: Optional configuration schema
        """
        if plugin_id in self._plugins:
            self._logger.warning("Plugin %s already registered, overwriting", plugin_id)
        
        metadata = PluginMetadata(
            plugin_id=plugin_id,
            name=name,
            version=version,
            description=description,
            plugin_type=plugin_type,
            entry_point=entry_point,
            config_schema=config_schema,
        )
        
        self._plugins[plugin_id] = metadata
        
        # Index by type
        if plugin_type not in self._plugins_by_type:
            self._plugins_by_type[plugin_type] = []
        if plugin_id not in self._plugins_by_type[plugin_type]:
            self._plugins_by_type[plugin_type].append(plugin_id)
        
        self._logger.info("Registered plugin: %s (%s)", plugin_id, name)
    
    def get(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin metadata.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            PluginMetadata or None
        """
        return self._plugins.get(plugin_id)
    
    def list_plugins(self, plugin_type: Optional[str] = None) -> List[PluginMetadata]:
        """List all plugins or plugins of a specific type.
        
        Args:
            plugin_type: Optional plugin type filter
            
        Returns:
            List of PluginMetadata
        """
        if plugin_type:
            plugin_ids = self._plugins_by_type.get(plugin_type, [])
            return [self._plugins[pid] for pid in plugin_ids if pid in self._plugins]
        return list(self._plugins.values())
    
    def unregister(self, plugin_id: str) -> bool:
        """Unregister a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if unregistered, False if not found
        """
        if plugin_id not in self._plugins:
            return False
        
        metadata = self._plugins[plugin_id]
        plugin_type = metadata.plugin_type
        
        # Remove from type index
        if plugin_type in self._plugins_by_type:
            if plugin_id in self._plugins_by_type[plugin_type]:
                self._plugins_by_type[plugin_type].remove(plugin_id)
        
        del self._plugins[plugin_id]
        self._logger.info("Unregistered plugin: %s", plugin_id)
        return True
    
    def get_entry_point(self, plugin_id: str) -> Optional[Any]:
        """Get plugin entry point.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Entry point or None
        """
        metadata = self.get(plugin_id)
        return metadata.entry_point if metadata else None
