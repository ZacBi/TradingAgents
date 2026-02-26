"""Workflow Configuration for TradingAgents.

Supports configuration-driven workflow definition.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkflowConfig:
    """Configuration-driven workflow definition.
    
    Allows defining workflow structure through configuration rather than code.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize workflow configuration.
        
        Args:
            config: Workflow configuration dictionary
        """
        self.config = config
        self._logger = logging.getLogger(__name__)
    
    def get_analysts(self) -> List[str]:
        """Get list of analysts to include.
        
        Returns:
            List of analyst keys
        """
        return self.config.get("analysts", ["market", "social", "news", "fundamentals"])
    
    def get_workflow_structure(self) -> Dict[str, Any]:
        """Get workflow structure definition.
        
        Returns:
            Dictionary defining workflow structure
        """
        return self.config.get("workflow", {})
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature: Feature name (e.g., "valuation", "deep_research", "experts", "trading")
            
        Returns:
            True if enabled, False otherwise
        """
        return self.config.get(f"{feature}_enabled", False)
    
    def get_feature_config(self, feature: str) -> Dict[str, Any]:
        """Get configuration for a specific feature.
        
        Args:
            feature: Feature name
            
        Returns:
            Feature configuration dictionary
        """
        return self.config.get(f"{feature}_config", {})
    
    @classmethod
    def from_file(cls, config_path: str) -> "WorkflowConfig":
        """Load workflow configuration from file.
        
        Args:
            config_path: Path to configuration file (JSON or YAML)
            
        Returns:
            WorkflowConfig instance
        """
        import json
        from pathlib import Path
        
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, "r") as f:
            if config_path.endswith(".yaml") or config_path.endswith(".yml"):
                try:
                    import yaml
                    config = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML required for YAML config files. Install with: pip install pyyaml")
            else:
                config = json.load(f)
        
        return cls(config)
    
    @classmethod
    def default_config(cls) -> "WorkflowConfig":
        """Get default workflow configuration.
        
        Returns:
            WorkflowConfig with default settings
        """
        default = {
            "analysts": ["market", "social", "news", "fundamentals"],
            "valuation_enabled": True,
            "deep_research_enabled": False,
            "experts_enabled": True,
            "trading_enabled": False,
            "workflow": {
                "debate_rounds": 1,
                "risk_rounds": 1,
            },
        }
        return cls(default)


class WorkflowBuilder:
    """Builder for creating workflows from configuration.
    
    Translates configuration into actual workflow structure.
    """
    
    def __init__(self, workflow_config: WorkflowConfig):
        """Initialize workflow builder.
        
        Args:
            workflow_config: WorkflowConfig instance
        """
        self.config = workflow_config
        self._logger = logging.getLogger(__name__)
    
    def build_workflow_options(self) -> Dict[str, Any]:
        """Build workflow options from configuration.
        
        Returns:
            Dictionary of workflow options
        """
        options = {
            "selected_analysts": self.config.get_analysts(),
            "valuation_enabled": self.config.is_feature_enabled("valuation"),
            "deep_research_enabled": self.config.is_feature_enabled("deep_research"),
            "experts_enabled": self.config.is_feature_enabled("experts"),
            "trading_enabled": self.config.is_feature_enabled("trading"),
        }
        
        # Add feature-specific configs
        workflow_structure = self.config.get_workflow_structure()
        if workflow_structure:
            options.update(workflow_structure)
        
        return options
    
    def apply_to_graph_setup(self, graph_setup: Any):
        """Apply configuration to GraphSetup instance.
        
        Args:
            graph_setup: GraphSetup instance
        """
        # Update config with workflow options
        workflow_options = self.build_workflow_options()
        if hasattr(graph_setup, "config"):
            graph_setup.config.update(workflow_options)
        
        # Apply feature configs
        if self.config.is_feature_enabled("trading"):
            trading_config = self.config.get_feature_config("trading")
            if hasattr(graph_setup, "config"):
                graph_setup.config["trading_config"] = trading_config
        
        if self.config.is_feature_enabled("risk"):
            risk_config = self.config.get_feature_config("risk")
            if hasattr(graph_setup, "config"):
                graph_setup.config["risk_config"] = risk_config
