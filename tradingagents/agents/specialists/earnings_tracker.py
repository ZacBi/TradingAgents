# TradingAgents/agents/specialists/earnings_tracker.py
"""Earnings Tracker for monitoring and alerting on upcoming earnings."""

import logging
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class EarningsAlert:
    """Alert for an upcoming earnings release."""
    ticker: str
    earnings_date: date
    days_until: int
    alert_type: str  # "upcoming", "imminent", "today"
    historical_surprise_rate: Optional[float] = None
    consensus_estimate: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "earnings_date": self.earnings_date.isoformat(),
            "days_until": self.days_until,
            "alert_type": self.alert_type,
            "historical_surprise_rate": self.historical_surprise_rate,
            "consensus_estimate": self.consensus_estimate,
        }


class EarningsTracker:
    """
    Tracks upcoming earnings dates and generates alerts.
    
    Features:
    - Check portfolio for upcoming earnings
    - Generate pre-earnings analysis alerts
    - Track historical earnings surprise rates
    - Support for custom alert thresholds
    """

    def __init__(self, config: dict):
        """
        Initialize the Earnings Tracker.
        
        Args:
            config: Configuration dictionary with keys:
                - earnings_tracking_enabled: Whether tracking is enabled
                - earnings_lookahead_days: Days to look ahead (default: 14)
                - earnings_imminent_days: Days for "imminent" alert (default: 3)
        """
        self.enabled = config.get("earnings_tracking_enabled", True)
        self.lookahead_days = config.get("earnings_lookahead_days", 14)
        self.imminent_days = config.get("earnings_imminent_days", 3)
        
        logger.info(
            "EarningsTracker initialized: enabled=%s, lookahead=%d days",
            self.enabled, self.lookahead_days
        )

    def check_upcoming_earnings(
        self,
        portfolio: list[str],
        reference_date: Optional[date] = None,
    ) -> list[EarningsAlert]:
        """
        Check portfolio stocks for upcoming earnings.
        
        Args:
            portfolio: List of ticker symbols
            reference_date: Date to check from (default: today)
            
        Returns:
            List of EarningsAlert objects for stocks with upcoming earnings
        """
        if not self.enabled:
            return []
        
        if reference_date is None:
            reference_date = date.today()
        
        alerts = []
        
        for ticker in portfolio:
            try:
                alert = self._check_ticker_earnings(ticker, reference_date)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.warning("Failed to check earnings for %s: %s", ticker, e)
        
        # Sort by days until earnings
        alerts.sort(key=lambda a: a.days_until)
        
        return alerts

    def _check_ticker_earnings(
        self,
        ticker: str,
        reference_date: date,
    ) -> Optional[EarningsAlert]:
        """Check a single ticker for upcoming earnings."""
        try:
            # Use the dataflows interface to get earnings dates
            from tradingagents.dataflows import get_data
            
            earnings_data = get_data("earnings_dates", ticker)
            
            if not earnings_data or "error" in earnings_data.lower():
                return None
            
            # Parse earnings dates from CSV format
            earnings_dates = self._parse_earnings_dates(earnings_data)
            
            # Find the next earnings date
            for ed in earnings_dates:
                if ed >= reference_date:
                    days_until = (ed - reference_date).days
                    
                    if days_until <= self.lookahead_days:
                        # Determine alert type
                        if days_until == 0:
                            alert_type = "today"
                        elif days_until <= self.imminent_days:
                            alert_type = "imminent"
                        else:
                            alert_type = "upcoming"
                        
                        return EarningsAlert(
                            ticker=ticker,
                            earnings_date=ed,
                            days_until=days_until,
                            alert_type=alert_type,
                        )
                    break
            
            return None
            
        except ImportError:
            logger.warning("dataflows module not available for earnings check")
            return None
        except Exception as e:
            logger.debug("Error checking earnings for %s: %s", ticker, e)
            return None

    def _parse_earnings_dates(self, data: str) -> list[date]:
        """Parse earnings dates from CSV data."""
        dates = []
        
        lines = data.strip().split("\n")
        for line in lines[1:]:  # Skip header
            try:
                parts = line.split(",")
                if parts:
                    date_str = parts[0].strip()
                    # Try common date formats
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"]:
                        try:
                            dt = datetime.strptime(date_str, fmt).date()
                            dates.append(dt)
                            break
                        except ValueError:
                            continue
            except Exception:
                continue
        
        dates.sort()
        return dates

    def generate_pre_earnings_analysis(
        self,
        ticker: str,
        earnings_date: date,
        llm=None,
    ) -> str:
        """
        Generate a pre-earnings analysis report.
        
        Args:
            ticker: Stock ticker
            earnings_date: Upcoming earnings date
            llm: Optional LLM for generating analysis
            
        Returns:
            Pre-earnings analysis report string
        """
        days_until = (earnings_date - date.today()).days
        
        # Build basic analysis without LLM
        report_parts = [
            f"## Pre-Earnings Analysis: {ticker}",
            f"**Earnings Date**: {earnings_date.isoformat()}",
            f"**Days Until**: {days_until}",
            "",
            "### Key Considerations",
            "- Review consensus EPS and revenue estimates",
            "- Check historical earnings surprise patterns",
            "- Monitor recent analyst revisions",
            "- Consider sector and macro trends",
            "- Evaluate guidance expectations",
            "",
            "### Risk Factors",
            "- Earnings announcements often cause significant price moves",
            "- Options implied volatility typically elevated pre-earnings",
            "- Consider position sizing and risk management",
        ]
        
        if llm:
            try:
                prompt = f"""Generate a brief pre-earnings analysis for {ticker}.
                
Earnings Date: {earnings_date}
Days Until Earnings: {days_until}

Focus on:
1. What to watch in the earnings report
2. Key metrics and expectations
3. Potential catalysts or risks
4. Historical earnings performance patterns

Keep the analysis concise (3-4 paragraphs)."""
                
                response = llm.invoke(prompt)
                report_parts.extend([
                    "",
                    "### AI Analysis",
                    response.content,
                ])
            except Exception as e:
                logger.warning("Failed to generate AI analysis: %s", e)
        
        return "\n".join(report_parts)

    def get_earnings_calendar(
        self,
        tickers: list[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """
        Get earnings calendar for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of earnings events sorted by date
        """
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=self.lookahead_days)
        
        events = []
        
        for ticker in tickers:
            alerts = self.check_upcoming_earnings([ticker], start_date)
            for alert in alerts:
                if alert.earnings_date <= end_date:
                    events.append({
                        "date": alert.earnings_date.isoformat(),
                        "ticker": ticker,
                        "days_until": alert.days_until,
                        "alert_type": alert.alert_type,
                    })
        
        # Sort by date
        events.sort(key=lambda e: e["date"])
        
        return events


def create_earnings_tracker(config: dict) -> EarningsTracker:
    """Factory function to create an EarningsTracker."""
    return EarningsTracker(config)


def create_earnings_tracker_node(llm, config: dict) -> Callable:
    """
    Factory function to create an Earnings Tracker agent node.
    
    Args:
        llm: Language model for generating analysis
        config: Configuration dictionary
        
    Returns:
        A node function for the LangGraph
    """
    tracker = EarningsTracker(config)
    
    def earnings_tracker_node(state: dict) -> dict:
        """Earnings tracker node that checks and alerts on upcoming earnings."""
        if not tracker.enabled:
            return {}
        
        ticker = state.get("company_of_interest")
        if not ticker:
            return {}
        
        # Check for upcoming earnings
        alerts = tracker.check_upcoming_earnings([ticker])
        
        if not alerts:
            return {"earnings_alert": None}
        
        alert = alerts[0]
        
        # Generate analysis if earnings are imminent
        analysis = None
        if alert.alert_type in ["imminent", "today"]:
            analysis = tracker.generate_pre_earnings_analysis(
                ticker, alert.earnings_date, llm
            )
        
        return {
            "earnings_alert": alert.to_dict(),
            "earnings_analysis": analysis,
        }
    
    return earnings_tracker_node
