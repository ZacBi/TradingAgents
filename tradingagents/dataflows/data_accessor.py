"""Data Accessor for TradingAgents.

Provides unified interface for data access with caching.
"""

import hashlib
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class DataAccessor:
    """Unified data accessor with caching.
    
    Provides:
    - Unified interface for data access
    - Caching mechanism to reduce API calls
    - Cache invalidation strategies
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize data accessor.
        
        Args:
            config: Configuration dictionary with:
                - cache_enabled: Whether caching is enabled (default: True)
                - cache_dir: Cache directory path (default: "./data_cache")
                - cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
                - cache_max_size: Maximum cache size in MB (default: 100)
        """
        self.config = config or {}
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_dir = Path(self.config.get("cache_dir", "./data_cache"))
        self.cache_ttl = self.config.get("cache_ttl", 3600)  # 1 hour default
        self.cache_max_size_mb = self.config.get("cache_max_size", 100)
        self._logger = logging.getLogger(__name__)
        
        # Create cache directory if enabled
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get data from cache.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        if not self.cache_enabled:
            return None
        
        cache_file = self.cache_dir / f"{self._hash_key(cache_key)}.cache"
        
        if not cache_file.exists():
            return None
        
        try:
            # Check if cache is expired
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - cache_time > timedelta(seconds=self.cache_ttl):
                self._logger.debug("Cache expired for key: %s", cache_key)
                cache_file.unlink()
                return None
            
            # Load cached data
            with open(cache_file, "rb") as f:
                cached = pickle.load(f)
            
            self._logger.debug("Cache hit for key: %s", cache_key)
            return cached.get("data")
        except Exception as e:
            self._logger.exception("Failed to load cache for key %s: %s", cache_key, e)
            return None
    
    def set_cached_data(self, cache_key: str, data: Any):
        """Set data in cache.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        if not self.cache_enabled:
            return
        
        try:
            cache_file = self.cache_dir / f"{self._hash_key(cache_key)}.cache"
            
            # Check cache size and clean if needed
            self._clean_cache_if_needed()
            
            # Save cached data
            with open(cache_file, "wb") as f:
                pickle.dump({
                    "key": cache_key,
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                }, f)
            
            self._logger.debug("Cached data for key: %s", cache_key)
        except Exception as e:
            self._logger.exception("Failed to cache data for key %s: %s", cache_key, e)
    
    def get_data(
        self,
        data_func: Callable,
        cache_key: str,
        *args,
        **kwargs
    ) -> Any:
        """Get data with caching.
        
        Args:
            data_func: Function to call for data
            cache_key: Cache key (should be unique per data request)
            *args: Positional arguments for data_func
            **kwargs: Keyword arguments for data_func
            
        Returns:
            Data from cache or data_func
        """
        # Try cache first
        cached_data = self.get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Call data function
        data = data_func(*args, **kwargs)
        
        # Cache the result
        self.set_cached_data(cache_key, data)
        
        return data
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache.
        
        Args:
            pattern: Optional pattern to match cache keys (None = clear all)
        """
        if not self.cache_dir.exists():
            return
        
        try:
            if pattern:
                # Clear matching cache files
                pattern_hash = self._hash_key(pattern)
                for cache_file in self.cache_dir.glob("*.cache"):
                    if pattern_hash in cache_file.name:
                        cache_file.unlink()
            else:
                # Clear all cache
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
            
            self._logger.info("Cache cleared (pattern: %s)", pattern or "all")
        except Exception as e:
            self._logger.exception("Failed to clear cache: %s", e)
    
    def _hash_key(self, key: str) -> str:
        """Hash cache key to filename-safe string.
        
        Args:
            key: Cache key
            
        Returns:
            Hashed key
        """
        return hashlib.md5(key.encode()).hexdigest()
    
    def _clean_cache_if_needed(self):
        """Clean cache if it exceeds max size."""
        if not self.cache_dir.exists():
            return
        
        try:
            # Calculate total cache size
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
            max_size_bytes = self.cache_max_size_mb * 1024 * 1024
            
            if total_size > max_size_bytes:
                # Remove oldest cache files
                cache_files = sorted(
                    self.cache_dir.glob("*.cache"),
                    key=lambda f: f.stat().st_mtime
                )
                
                # Remove oldest files until under limit
                for cache_file in cache_files:
                    if total_size <= max_size_bytes:
                        break
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    total_size -= file_size
                    self._logger.debug("Removed old cache file: %s", cache_file.name)
        except Exception as e:
            self._logger.exception("Failed to clean cache: %s", e)
