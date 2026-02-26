"""Trading Agent Scheduler using APScheduler.

Enables scheduled execution of trading agent workflows.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class TradingAgentScheduler:
    """Scheduler for TradingAgents long-run agent.
    
    Uses APScheduler to schedule periodic execution of trading workflows.
    """
    
    def __init__(self, timezone: str = "UTC"):
        """Initialize scheduler.
        
        Args:
            timezone: Timezone for scheduled tasks (default: UTC)
        """
        self.scheduler = BackgroundScheduler(timezone=timezone)
        self._logger = logging.getLogger(__name__)
        self._jobs = {}
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self._logger.info("TradingAgentScheduler started")
    
    def stop(self, wait: bool = True):
        """Stop the scheduler.
        
        Args:
            wait: Whether to wait for running jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            self._logger.info("TradingAgentScheduler stopped")
    
    def add_daily_job(
        self,
        job_id: str,
        func: Callable,
        hour: int = 9,
        minute: int = 30,
        timezone: Optional[str] = None,
        **kwargs
    ):
        """Add a daily scheduled job (e.g., market open analysis).
        
        Args:
            job_id: Unique job identifier
            func: Function to execute
            hour: Hour of day (0-23)
            minute: Minute of hour (0-59)
            timezone: Optional timezone override
            **kwargs: Additional arguments to pass to the function
        """
        trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone or self.scheduler.timezone)
        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        self._jobs[job_id] = job
        self._logger.info("Added daily job: %s at %02d:%02d", job_id, hour, minute)
        return job
    
    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        minutes: int = 60,
        **kwargs
    ):
        """Add an interval-based scheduled job.
        
        Args:
            job_id: Unique job identifier
            func: Function to execute
            minutes: Interval in minutes
            **kwargs: Additional arguments to pass to the function
        """
        trigger = IntervalTrigger(minutes=minutes)
        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        self._jobs[job_id] = job
        self._logger.info("Added interval job: %s every %d minutes", job_id, minutes)
        return job
    
    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expression: str,
        **kwargs
    ):
        """Add a cron-based scheduled job.
        
        Args:
            job_id: Unique job identifier
            func: Function to execute
            cron_expression: Cron expression (e.g., "0 9 * * 1-5" for weekdays at 9 AM)
            **kwargs: Additional arguments to pass to the function
        """
        # Parse cron expression (simplified - APScheduler uses different format)
        # For full cron support, consider using croniter
        trigger = CronTrigger.from_crontab(cron_expression)
        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        self._jobs[job_id] = job
        self._logger.info("Added cron job: %s with expression: %s", job_id, cron_expression)
        return job
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job.
        
        Args:
            job_id: Job identifier
        """
        if job_id in self._jobs:
            self.scheduler.remove_job(job_id)
            del self._jobs[job_id]
            self._logger.info("Removed job: %s", job_id)
    
    def list_jobs(self) -> list:
        """List all scheduled jobs.
        
        Returns:
            List of job metadata
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            })
        return jobs
    
    def get_job(self, job_id: str) -> Optional[Any]:
        """Get a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job object or None
        """
        return self.scheduler.get_job(job_id)
    
    def pause_job(self, job_id: str):
        """Pause a scheduled job.
        
        Args:
            job_id: Job identifier
        """
        job = self.get_job(job_id)
        if job:
            job.pause()
            self._logger.info("Paused job: %s", job_id)
    
    def resume_job(self, job_id: str):
        """Resume a paused job.
        
        Args:
            job_id: Job identifier
        """
        job = self.get_job(job_id)
        if job:
            job.resume()
            self._logger.info("Resumed job: %s", job_id)
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.scheduler.running
