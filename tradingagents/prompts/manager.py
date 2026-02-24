# TradingAgents/prompts/manager.py
"""Langfuse Prompt Management integration.

Provides centralized prompt management with:
- Langfuse cloud/self-hosted integration
- Local fallback for reliability
- TTL-based caching
- Hot reload support
"""

import logging
import os
import time
from typing import Any, Dict, Optional

from .fallback import FALLBACK_TEMPLATES, get_fallback_template
from .registry import PromptNames, PROMPT_LABELS

logger = logging.getLogger(__name__)


class PromptManager:
    """Centralized prompt manager with Langfuse integration.
    
    Features:
    - Fetches prompts from Langfuse Prompt Management
    - Falls back to local templates when Langfuse is unavailable
    - Caches prompts with configurable TTL
    - Supports version pinning for production stability
    
    Usage:
        pm = PromptManager(config)
        prompt = pm.get_prompt("expert-buffett", variables={"market_report": "..."})
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the PromptManager.
        
        Args:
            config: Configuration dict with keys:
                - prompt_management_enabled: bool (default: True)
                - prompt_cache_ttl: int seconds (default: 300)
                - prompt_fallback_enabled: bool (default: True)
                - prompt_version: str or None (default: None = production)
                - langfuse_public_key: str (or env LANGFUSE_PUBLIC_KEY)
                - langfuse_secret_key: str (or env LANGFUSE_SECRET_KEY)
                - langfuse_host: str (default: http://localhost:3000)
        """
        self._config = config or {}
        self._enabled = self._config.get("prompt_management_enabled", True)
        self._cache_ttl = self._config.get("prompt_cache_ttl", 300)
        self._fallback_enabled = self._config.get("prompt_fallback_enabled", True)
        self._version = self._config.get("prompt_version", None)
        
        # Cache: {name: {"template": str, "expires_at": float}}
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Langfuse client (lazy init)
        self._langfuse = None
        self._langfuse_available = False
        
        if self._enabled:
            self._init_langfuse()
    
    def _init_langfuse(self) -> None:
        """Initialize Langfuse client."""
        public_key = self._config.get("langfuse_public_key") or os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = self._config.get("langfuse_secret_key") or os.environ.get("LANGFUSE_SECRET_KEY")
        host = self._config.get("langfuse_host") or os.environ.get("LANGFUSE_HOST", "http://localhost:3000")
        
        if not public_key or not secret_key:
            logger.debug(
                "Langfuse keys not configured for prompt management. "
                "Using local fallback templates."
            )
            return
        
        try:
            from langfuse import Langfuse
            
            self._langfuse = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            self._langfuse_available = True
            logger.info("Langfuse prompt management enabled (host=%s)", host)
            
        except ImportError:
            logger.warning(
                "langfuse package not installed. Using local fallback templates. "
                "Install with: pip install langfuse"
            )
        except Exception as exc:
            logger.warning("Failed to initialize Langfuse for prompts: %s", exc)
    
    def get_prompt(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
    ) -> str:
        """Get a compiled prompt by name.
        
        Args:
            name: Prompt name from PromptNames (e.g., "expert-buffett")
            variables: Dict of variables to substitute in the template
            version: Optional version override (default: use config version)
            
        Returns:
            The compiled prompt string with variables substituted
            
        Raises:
            KeyError: If prompt not found and fallback disabled
        """
        variables = variables or {}
        version = version or self._version
        
        # Get template (from cache, Langfuse, or fallback)
        template = self._get_template(name, version)
        
        # Compile template with variables
        try:
            return template.format(**variables)
        except KeyError as e:
            # Missing variable - return template with partial substitution
            logger.warning("Missing variable %s for prompt %s, using partial format", e, name)
            return template.format_map(SafeDict(variables))
    
    def _get_template(self, name: str, version: Optional[str] = None) -> str:
        """Get raw template string (before variable substitution).
        
        Tries in order:
        1. Cache (if not expired)
        2. Langfuse
        3. Local fallback
        """
        cache_key = f"{name}:{version or 'latest'}"
        
        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() < cached["expires_at"]:
                return cached["template"]
            else:
                # Cache expired
                del self._cache[cache_key]
        
        # Try Langfuse
        template = None
        if self._langfuse_available:
            template = self._fetch_from_langfuse(name, version)
        
        # Fallback to local
        if template is None and self._fallback_enabled:
            template = self._get_fallback(name)
        
        if template is None:
            raise KeyError(f"Prompt '{name}' not found and fallback disabled")
        
        # Cache the template
        if self._cache_ttl > 0:
            self._cache[cache_key] = {
                "template": template,
                "expires_at": time.time() + self._cache_ttl,
            }
        
        return template
    
    def _fetch_from_langfuse(self, name: str, version: Optional[str] = None) -> Optional[str]:
        """Fetch prompt template from Langfuse.
        
        Args:
            name: Prompt name
            version: Optional specific version
            
        Returns:
            Template string or None if fetch fails
        """
        try:
            # Langfuse get_prompt API
            if version:
                prompt = self._langfuse.get_prompt(name, version=version)
            else:
                prompt = self._langfuse.get_prompt(name)
            
            # Langfuse prompt object has .prompt attribute for text prompts
            # or .compile() method for chat prompts
            if hasattr(prompt, "prompt"):
                return prompt.prompt
            elif hasattr(prompt, "compile"):
                # For chat prompts, get the compiled string
                compiled = prompt.compile()
                if isinstance(compiled, str):
                    return compiled
                elif isinstance(compiled, list):
                    # Chat format - extract content
                    return "\n".join(
                        msg.get("content", "") for msg in compiled if isinstance(msg, dict)
                    )
            
            logger.warning("Unexpected Langfuse prompt format for %s", name)
            return None
            
        except Exception as exc:
            logger.debug("Failed to fetch prompt '%s' from Langfuse: %s", name, exc)
            return None
    
    def _get_fallback(self, name: str) -> Optional[str]:
        """Get fallback template from local storage."""
        try:
            return get_fallback_template(name)
        except KeyError:
            logger.warning("No fallback template for prompt '%s'", name)
            return None
    
    def clear_cache(self) -> None:
        """Clear all cached prompts."""
        self._cache.clear()
        logger.debug("Prompt cache cleared")
    
    def invalidate(self, name: str) -> None:
        """Invalidate cache for a specific prompt.
        
        Args:
            name: Prompt name to invalidate
        """
        keys_to_remove = [k for k in self._cache if k.startswith(f"{name}:")]
        for key in keys_to_remove:
            del self._cache[key]
        logger.debug("Invalidated cache for prompt '%s'", name)
    
    def list_prompts(self) -> list:
        """List all available prompt names."""
        return list(FALLBACK_TEMPLATES.keys())
    
    def is_available(self) -> bool:
        """Check if Langfuse is available."""
        return self._langfuse_available
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        valid_entries = sum(1 for v in self._cache.values() if v["expires_at"] > now)
        return {
            "cache_size": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "langfuse_available": self._langfuse_available,
            "fallback_enabled": self._fallback_enabled,
        }


class SafeDict(dict):
    """Dict that returns {key} for missing keys during format_map."""
    
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


# Global singleton instance (lazy initialized)
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(config: Optional[Dict[str, Any]] = None) -> PromptManager:
    """Get or create the global PromptManager instance.
    
    Args:
        config: Configuration dict (only used on first call)
        
    Returns:
        The global PromptManager instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager(config)
    return _prompt_manager


def reset_prompt_manager() -> None:
    """Reset the global PromptManager instance.
    
    Use this for testing or when config changes.
    """
    global _prompt_manager
    _prompt_manager = None
