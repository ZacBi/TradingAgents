"""Error Recovery Mechanism for TradingAgents.

Provides automatic error recovery and retry logic for workflow execution.
"""

import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error types for classification."""
    TRANSIENT = "transient"  # Temporary errors that may resolve on retry
    PERMANENT = "permanent"  # Errors that won't resolve on retry
    RATE_LIMIT = "rate_limit"  # Rate limiting errors
    NETWORK = "network"  # Network-related errors
    API_ERROR = "api_error"  # API-specific errors
    VALIDATION = "validation"  # Validation errors
    UNKNOWN = "unknown"  # Unknown error type


class ErrorRecovery:
    """Error recovery mechanism for TradingAgents.
    
    Provides:
    - Error classification
    - Retry logic with exponential backoff
    - Error recovery strategies
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize error recovery.
        
        Args:
            config: Configuration dictionary with:
                - max_retries: Maximum number of retries (default: 3)
                - retry_delay: Initial retry delay in seconds (default: 1.0)
                - backoff_multiplier: Exponential backoff multiplier (default: 2.0)
                - retryable_errors: List of error types to retry
        """
        self.config = config or {}
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)
        self.backoff_multiplier = self.config.get("backoff_multiplier", 2.0)
        self.retryable_errors = self.config.get("retryable_errors", [
            ErrorType.TRANSIENT,
            ErrorType.RATE_LIMIT,
            ErrorType.NETWORK,
        ])
        self._logger = logging.getLogger(__name__)
    
    def classify_error(self, error: Exception) -> ErrorType:
        """Classify error type.
        
        Args:
            error: Exception to classify
            
        Returns:
            ErrorType enum
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Network errors
        if any(keyword in error_str for keyword in ["connection", "timeout", "network", "dns"]):
            return ErrorType.NETWORK
        
        # Rate limit errors
        if any(keyword in error_str for keyword in ["rate limit", "429", "too many requests", "quota"]):
            return ErrorType.RATE_LIMIT
        
        # API errors
        if any(keyword in error_str for keyword in ["api", "http", "status code", "401", "403", "500"]):
            return ErrorType.API_ERROR
        
        # Validation errors
        if any(keyword in error_str for keyword in ["validation", "invalid", "missing", "required"]):
            return ErrorType.VALIDATION
        
        # Transient errors (common patterns)
        if any(keyword in error_str for keyword in ["temporary", "retry", "unavailable", "503", "502"]):
            return ErrorType.TRANSIENT
        
        # Check error type
        if "Timeout" in error_type or "Connection" in error_type:
            return ErrorType.NETWORK
        
        return ErrorType.UNKNOWN
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if error should be retried.
        
        Args:
            error: Exception that occurred
            attempt: Current attempt number (1-indexed)
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt > self.max_retries:
            return False
        
        error_type = self.classify_error(error)
        return error_type in self.retryable_errors
    
    def get_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff.
        
        Args:
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.retry_delay * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, 60.0)  # Cap at 60 seconds
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> tuple[Any, Optional[Exception]]:
        """Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Tuple of (result, error)
            - If successful: (result, None)
            - If failed after retries: (None, last_exception)
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    self._logger.info("Function succeeded on attempt %d", attempt)
                return result, None
            except Exception as e:
                last_error = e
                error_type = self.classify_error(e)
                
                if not self.should_retry(e, attempt):
                    self._logger.warning(
                        "Error not retryable (type: %s): %s", error_type.value, str(e)
                    )
                    return None, e
                
                if attempt < self.max_retries:
                    delay = self.get_retry_delay(attempt)
                    self._logger.warning(
                        "Attempt %d failed (type: %s): %s. Retrying in %.2fs...",
                        attempt, error_type.value, str(e), delay
                    )
                    time.sleep(delay)
                else:
                    self._logger.error(
                        "All %d attempts failed. Last error (type: %s): %s",
                        self.max_retries, error_type.value, str(e)
                    )
        
        return None, last_error
    
    def recover_from_error(
        self,
        error: Exception,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Attempt to recover from error.
        
        Args:
            error: Exception that occurred
            context: Context information (state, node, etc.)
            
        Returns:
            Recovery action dictionary or None if recovery not possible
        """
        error_type = self.classify_error(error)
        
        # Recovery strategies based on error type
        if error_type == ErrorType.RATE_LIMIT:
            return {
                "action": "wait",
                "delay": self.get_retry_delay(1),
                "message": "Rate limit hit, waiting before retry",
            }
        
        if error_type == ErrorType.NETWORK:
            return {
                "action": "retry",
                "delay": self.get_retry_delay(1),
                "message": "Network error, will retry",
            }
        
        if error_type == ErrorType.TRANSIENT:
            return {
                "action": "retry",
                "delay": self.get_retry_delay(1),
                "message": "Transient error, will retry",
            }
        
        # For permanent errors, suggest skipping or using fallback
        if error_type == ErrorType.PERMANENT or error_type == ErrorType.VALIDATION:
            return {
                "action": "skip",
                "message": f"Permanent error: {str(error)}",
            }
        
        return None
