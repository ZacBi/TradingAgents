"""Metrics Collector for TradingAgents.

Provides Prometheus metrics for monitoring.
"""

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import Prometheus client, but make it optional
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available. Install with: pip install prometheus-client")


class MetricsCollector:
    """Collects and exposes Prometheus metrics for TradingAgents.
    
    Metrics tracked:
    - Agent execution count and duration
    - LLM API calls and errors
    - Database operations
    - Checkpoint operations
    - Trading decisions
    """
    
    def __init__(self, enable_prometheus: bool = True, prometheus_port: int = 8000):
        """Initialize metrics collector.
        
        Args:
            enable_prometheus: Whether to enable Prometheus metrics
            prometheus_port: Port for Prometheus HTTP server
        """
        self._logger = logging.getLogger(__name__)
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        self.prometheus_port = prometheus_port
        
        if self.enable_prometheus:
            self._init_prometheus_metrics()
            self._start_prometheus_server()
        else:
            self._logger.warning("Prometheus metrics disabled (prometheus_client not available)")
            self._init_null_metrics()
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        # Agent execution metrics
        self.agent_executions_total = Counter(
            "tradingagents_agent_executions_total",
            "Total number of agent executions",
            ["agent_type", "status"]
        )
        
        self.agent_execution_duration = Histogram(
            "tradingagents_agent_execution_duration_seconds",
            "Agent execution duration in seconds",
            ["agent_type"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        # LLM metrics
        self.llm_calls_total = Counter(
            "tradingagents_llm_calls_total",
            "Total number of LLM API calls",
            ["provider", "model", "status"]
        )
        
        self.llm_call_duration = Histogram(
            "tradingagents_llm_call_duration_seconds",
            "LLM API call duration in seconds",
            ["provider", "model"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        # Database metrics
        self.database_operations_total = Counter(
            "tradingagents_database_operations_total",
            "Total number of database operations",
            ["operation", "status"]
        )
        
        # Checkpoint metrics
        self.checkpoint_operations_total = Counter(
            "tradingagents_checkpoint_operations_total",
            "Total number of checkpoint operations",
            ["operation", "status"]
        )
        
        # Trading decision metrics
        self.trading_decisions_total = Counter(
            "tradingagents_trading_decisions_total",
            "Total number of trading decisions",
            ["decision_type"]
        )
        
        # System metrics
        self.active_threads = Gauge(
            "tradingagents_active_threads",
            "Number of active agent threads"
        )
        
        self._logger.info("Prometheus metrics initialized")
    
    def _init_null_metrics(self):
        """Initialize null metrics (no-op when Prometheus is not available)."""
        class NullMetric:
            def inc(self, *args, **kwargs): pass
            def observe(self, *args, **kwargs): pass
            def set(self, *args, **kwargs): pass
        
        self.agent_executions_total = NullMetric()
        self.agent_execution_duration = NullMetric()
        self.llm_calls_total = NullMetric()
        self.llm_call_duration = NullMetric()
        self.database_operations_total = NullMetric()
        self.checkpoint_operations_total = NullMetric()
        self.trading_decisions_total = NullMetric()
        self.active_threads = NullMetric()
    
    def _start_prometheus_server(self):
        """Start Prometheus HTTP server."""
        try:
            start_http_server(self.prometheus_port)
            self._logger.info("Prometheus metrics server started on port %d", self.prometheus_port)
        except Exception as e:
            self._logger.warning("Failed to start Prometheus server: %s", e)
    
    def record_agent_execution(self, agent_type: str, success: bool, duration: float):
        """Record agent execution metric.
        
        Args:
            agent_type: Type of agent (e.g., "market_analyst")
            success: Whether execution was successful
            duration: Execution duration in seconds
        """
        status = "success" if success else "failure"
        self.agent_executions_total.labels(agent_type=agent_type, status=status).inc()
        self.agent_execution_duration.labels(agent_type=agent_type).observe(duration)
    
    def record_llm_call(self, provider: str, model: str, success: bool, duration: float):
        """Record LLM API call metric.
        
        Args:
            provider: LLM provider (e.g., "openai")
            model: Model name (e.g., "gpt-4")
            success: Whether call was successful
            duration: Call duration in seconds
        """
        status = "success" if success else "failure"
        self.llm_calls_total.labels(provider=provider, model=model, status=status).inc()
        self.llm_call_duration.labels(provider=provider, model=model).observe(duration)
    
    def record_database_operation(self, operation: str, success: bool):
        """Record database operation metric.
        
        Args:
            operation: Operation type (e.g., "save_decision")
            success: Whether operation was successful
        """
        status = "success" if success else "failure"
        self.database_operations_total.labels(operation=operation, status=status).inc()
    
    def record_checkpoint_operation(self, operation: str, success: bool):
        """Record checkpoint operation metric.
        
        Args:
            operation: Operation type (e.g., "save", "load")
            success: Whether operation was successful
        """
        status = "success" if success else "failure"
        self.checkpoint_operations_total.labels(operation=operation, status=status).inc()
    
    def record_trading_decision(self, decision_type: str):
        """Record trading decision metric.
        
        Args:
            decision_type: Decision type (e.g., "BUY", "SELL", "HOLD")
        """
        self.trading_decisions_total.labels(decision_type=decision_type).inc()
    
    def set_active_threads(self, count: int):
        """Set active threads gauge.
        
        Args:
            count: Number of active threads
        """
        self.active_threads.set(count)
