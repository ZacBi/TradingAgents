"""Long-Run Agent Integration for TradingAgents.

Provides integration of scheduler, monitoring, and recovery for continuous operation.
"""

import logging
from typing import Any, Callable, Optional

from tradingagents.monitoring import HealthMonitor, MetricsCollector
from tradingagents.scheduler import TradingAgentScheduler

logger = logging.getLogger(__name__)


class LongRunAgent:
    """Long-run agent wrapper for TradingAgents.
    
    Integrates:
    - Scheduler for periodic execution
    - Health monitoring
    - Metrics collection
    - State recovery
    """
    
    def __init__(
        self,
        trading_graph: Any,
        scheduler: Optional[TradingAgentScheduler] = None,
        health_monitor: Optional[HealthMonitor] = None,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        """Initialize long-run agent.
        
        Args:
            trading_graph: TradingAgentsGraph instance
            scheduler: Optional scheduler instance (created if None)
            health_monitor: Optional health monitor instance (created if None)
            metrics_collector: Optional metrics collector instance (created if None)
        """
        self.trading_graph = trading_graph
        self.scheduler = scheduler or TradingAgentScheduler()
        self.health_monitor = health_monitor or HealthMonitor()
        self.metrics_collector = metrics_collector or MetricsCollector()
        self._logger = logging.getLogger(__name__)
        self._running = False
    
    def start(self):
        """Start the long-run agent."""
        if self._running:
            self._logger.warning("Long-run agent is already running")
            return
        
        # Start scheduler
        self.scheduler.start()
        
        # Perform initial health check
        health_status = self.health_monitor.check_health(
            checkpointer=self.trading_graph.checkpointer,
            db_manager=self.trading_graph.db,
        )
        self._logger.info("Initial health check: %s", health_status["status"])
        
        self._running = True
        self._logger.info("Long-run agent started")
    
    def stop(self):
        """Stop the long-run agent."""
        if not self._running:
            return
        
        self.scheduler.stop(wait=True)
        self._running = False
        self._logger.info("Long-run agent stopped")
    
    def schedule_daily_analysis(
        self,
        company_name: str,
        hour: int = 9,
        minute: int = 30,
        timezone: Optional[str] = None,
    ):
        """Schedule daily analysis for a company.
        
        Args:
            company_name: Company ticker symbol
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)
            timezone: Optional timezone override
        """
        from datetime import datetime
        
        def run_analysis():
            trade_date = datetime.now().strftime("%Y-%m-%d")
            self._logger.info("Running scheduled analysis for %s on %s", company_name, trade_date)
            
            try:
                # Record start time for metrics
                import time
                start_time = time.time()
                
                # Run analysis
                final_state, signal = self.trading_graph.propagate(company_name, trade_date)
                
                # Record metrics
                duration = time.time() - start_time
                self.metrics_collector.record_agent_execution(
                    agent_type="full_workflow",
                    success=True,
                    duration=duration,
                )
                
                self._logger.info("Analysis completed: %s", signal)
            except Exception as e:
                self._logger.exception("Scheduled analysis failed: %s", e)
                self.metrics_collector.record_agent_execution(
                    agent_type="full_workflow",
                    success=False,
                    duration=0,
                )
        
        job_id = f"daily_analysis_{company_name}"
        self.scheduler.add_daily_job(
            job_id=job_id,
            func=run_analysis,
            hour=hour,
            minute=minute,
            timezone=timezone,
        )
        self._logger.info("Scheduled daily analysis for %s at %02d:%02d", company_name, hour, minute)
    
    def schedule_interval_analysis(
        self,
        company_name: str,
        minutes: int = 60,
    ):
        """Schedule interval-based analysis for a company.
        
        Args:
            company_name: Company ticker symbol
            minutes: Interval in minutes
        """
        from datetime import datetime
        
        def run_analysis():
            trade_date = datetime.now().strftime("%Y-%m-%d")
            self._logger.info("Running interval analysis for %s on %s", company_name, trade_date)
            
            try:
                import time
                start_time = time.time()
                
                final_state, signal = self.trading_graph.propagate(company_name, trade_date)
                
                duration = time.time() - start_time
                self.metrics_collector.record_agent_execution(
                    agent_type="full_workflow",
                    success=True,
                    duration=duration,
                )
            except Exception as e:
                self._logger.exception("Interval analysis failed: %s", e)
                self.metrics_collector.record_agent_execution(
                    agent_type="full_workflow",
                    success=False,
                    duration=0,
                )
        
        job_id = f"interval_analysis_{company_name}"
        self.scheduler.add_interval_job(
            job_id=job_id,
            func=run_analysis,
            minutes=minutes,
        )
        self._logger.info("Scheduled interval analysis for %s every %d minutes", company_name, minutes)
    
    def get_health_status(self) -> dict:
        """Get current health status.
        
        Returns:
            Health status dictionary
        """
        return self.health_monitor.check_health(
            checkpointer=self.trading_graph.checkpointer,
            db_manager=self.trading_graph.db,
        )
    
    def list_scheduled_jobs(self) -> list:
        """List all scheduled jobs.
        
        Returns:
            List of job metadata
        """
        return self.scheduler.list_jobs()
    
    @property
    def is_running(self) -> bool:
        """Check if long-run agent is running."""
        return self._running
