"""Plugin Manager for TradingAgents.

Handles plugin loading, initialization, and lifecycle management.
"""

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from tradingagents.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin loading and lifecycle.
    
    Supports:
    - Dynamic plugin loading from filesystem
    - Plugin discovery
    - Plugin initialization and configuration
    """
    
    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """Initialize plugin manager.
        
        Args:
            plugin_dirs: Optional list of directories to search for plugins
        """
        self.registry = PluginRegistry()
        self.plugin_dirs = plugin_dirs or []
        self._loaded_plugins: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)
    
    def load_plugin_from_module(self, module_path: str, plugin_id: Optional[str] = None) -> bool:
        """Load a plugin from a Python module.
        
        Args:
            module_path: Module path (e.g., "my_plugins.custom_analyst")
            plugin_id: Optional plugin ID (defaults to module name)
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            module = importlib.import_module(module_path)
            
            # Look for plugin registration function or class
            if hasattr(module, "register_plugin"):
                plugin_id = plugin_id or module_path.split(".")[-1]
                module.register_plugin(self.registry)
                self._logger.info("Loaded plugin from module: %s", module_path)
                return True
            elif hasattr(module, "PLUGIN_METADATA"):
                # Plugin defines metadata dict
                metadata = module.PLUGIN_METADATA
                plugin_id = plugin_id or metadata.get("plugin_id", module_path.split(".")[-1])
                self.registry.register(
                    plugin_id=plugin_id,
                    name=metadata.get("name", plugin_id),
                    version=metadata.get("version", "1.0.0"),
                    description=metadata.get("description", ""),
                    plugin_type=metadata.get("plugin_type", "agent"),
                    entry_point=metadata.get("entry_point"),
                    config_schema=metadata.get("config_schema"),
                )
                self._logger.info("Loaded plugin from module: %s", module_path)
                return True
            else:
                self._logger.warning("Module %s does not define plugin registration", module_path)
                return False
        except Exception as e:
            self._logger.exception("Failed to load plugin from module %s: %s", module_path, e)
            return False
    
    def load_plugins_from_directory(self, directory: str) -> int:
        """Load all plugins from a directory.
        
        Args:
            directory: Directory path to search
            
        Returns:
            Number of plugins loaded
        """
        plugin_dir = Path(directory)
        if not plugin_dir.exists():
            self._logger.warning("Plugin directory does not exist: %s", directory)
            return 0
        
        loaded_count = 0
        
        # Look for Python files or packages
        for item in plugin_dir.iterdir():
            if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                # Try to import as module
                module_name = item.stem
                try:
                    # Add directory to path temporarily
                    sys.path.insert(0, str(plugin_dir.parent))
                    module_path = f"{plugin_dir.name}.{module_name}"
                    if self.load_plugin_from_module(module_path):
                        loaded_count += 1
                except Exception as e:
                    self._logger.exception("Failed to load plugin from file %s: %s", item, e)
                finally:
                    if str(plugin_dir.parent) in sys.path:
                        sys.path.remove(str(plugin_dir.parent))
            elif item.is_dir() and (item / "__init__.py").exists():
                # Try to import as package
                try:
                    sys.path.insert(0, str(plugin_dir.parent))
                    module_path = f"{plugin_dir.name}.{item.name}"
                    if self.load_plugin_from_module(module_path):
                        loaded_count += 1
                except Exception as e:
                    self._logger.exception("Failed to load plugin from package %s: %s", item, e)
                finally:
                    if str(plugin_dir.parent) in sys.path:
                        sys.path.remove(str(plugin_dir.parent))
        
        self._logger.info("Loaded %d plugins from directory: %s", loaded_count, directory)
        return loaded_count
    
    def discover_and_load_plugins(self) -> int:
        """Discover and load plugins from configured directories.
        
        Returns:
            Number of plugins loaded
        """
        total_loaded = 0
        for plugin_dir in self.plugin_dirs:
            total_loaded += self.load_plugins_from_directory(plugin_dir)
        return total_loaded
    
    def create_plugin_instance(
        self,
        plugin_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Create an instance of a plugin.
        
        Args:
            plugin_id: Plugin identifier
            config: Optional configuration for the plugin
            
        Returns:
            Plugin instance or None
        """
        metadata = self.registry.get(plugin_id)
        if not metadata:
            self._logger.error("Plugin not found: %s", plugin_id)
            return None
        
        try:
            entry_point = metadata.entry_point
            
            # If entry_point is a class, instantiate it
            if isinstance(entry_point, type):
                if config:
                    instance = entry_point(**config)
                else:
                    instance = entry_point()
            # If entry_point is a function, call it
            elif callable(entry_point):
                if config:
                    instance = entry_point(**config)
                else:
                    instance = entry_point()
            else:
                instance = entry_point
            
            self._loaded_plugins[plugin_id] = instance
            self._logger.info("Created instance of plugin: %s", plugin_id)
            return instance
        except Exception as e:
            self._logger.exception("Failed to create plugin instance %s: %s", plugin_id, e)
            return None
    
    def get_plugin_instance(self, plugin_id: str) -> Optional[Any]:
        """Get a previously created plugin instance.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin instance or None
        """
        return self._loaded_plugins.get(plugin_id)
    
    def list_available_plugins(self, plugin_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available plugins.
        
        Args:
            plugin_type: Optional plugin type filter
            
        Returns:
            List of plugin information dictionaries
        """
        plugins = self.registry.list_plugins(plugin_type)
        return [
            {
                "plugin_id": p.plugin_id,
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "plugin_type": p.plugin_type,
            }
            for p in plugins
        ]
