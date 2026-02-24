"""Model routing configuration loader.

Loads model_routing.yaml, resolves ${alias} references,
and provides role-based model resolution for agent nodes.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class ModelRoutingConfig:
    """Resolves agent role types to concrete model names via YAML profiles."""

    def __init__(self, config_path: str, active_profile: Optional[str] = None):
        raw = self._load_yaml(config_path)
        self.aliases: Dict[str, str] = raw.get("model_aliases", {})
        self.profiles: Dict[str, dict] = raw.get("profiles", {})
        self.active_profile: str = active_profile or raw.get("active_profile", "balanced")

        if self.active_profile not in self.profiles:
            raise ValueError(
                f"Active profile '{self.active_profile}' not found. "
                f"Available: {list(self.profiles.keys())}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_model(self, role_type: str) -> str:
        """Resolve a role type to a concrete model name.

        Args:
            role_type: One of data_analyst, researcher, expert, trader,
                       judge, signal.

        Returns:
            Resolved model name string.

        Raises:
            KeyError: If the role_type is not defined in the active profile.
        """
        profile = self.profiles[self.active_profile]
        raw_value = profile[role_type]
        return self._resolve(raw_value)

    def get_fallback_chain(self) -> List[str]:
        """Return the resolved fallback model chain for the active profile."""
        profile = self.profiles[self.active_profile]
        raw_chain = profile.get("fallback_chain", [])
        return [self._resolve(v) for v in raw_chain]

    def list_profiles(self) -> List[str]:
        """Return all available profile names."""
        return list(self.profiles.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    _ALIAS_RE = re.compile(r"\$\{(\w+)\}")

    def _resolve(self, value: str) -> str:
        """Replace ${alias_name} with actual model name from aliases."""
        def _sub(match):
            alias = match.group(1)
            if alias not in self.aliases:
                raise KeyError(f"Unknown model alias: '{alias}'")
            return self.aliases[alias]
        return self._ALIAS_RE.sub(_sub, value)

    @staticmethod
    def _load_yaml(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


def load_model_routing(
    config_path: Optional[str] = None,
    active_profile: Optional[str] = None,
) -> ModelRoutingConfig:
    """Convenience loader that searches common locations.

    Search order:
      1. Explicit ``config_path``
      2. ``MODEL_ROUTING_CONFIG`` environment variable
      3. ``model_routing.yaml`` in the project root (next to pyproject.toml)
    """
    if config_path and os.path.isfile(config_path):
        return ModelRoutingConfig(config_path, active_profile)

    env_path = os.environ.get("MODEL_ROUTING_CONFIG")
    if env_path and os.path.isfile(env_path):
        return ModelRoutingConfig(env_path, active_profile)

    # Walk up from this file to find project root
    project_root = Path(__file__).resolve().parent.parent.parent
    default_path = project_root / "model_routing.yaml"
    if default_path.is_file():
        return ModelRoutingConfig(str(default_path), active_profile)

    raise FileNotFoundError(
        "model_routing.yaml not found. Provide config_path, set "
        "MODEL_ROUTING_CONFIG env var, or place it in the project root."
    )
