from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from tradingagents.database import DatabaseManager


class PortfolioService:
    """Read-only portfolio/positions/NAV helpers built on DatabaseManager."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def get_positions(self) -> List[Dict[str, Any]]:
        """Return all open positions as dicts."""
        return self._db.get_positions()

    def get_nav_history(
        self,
        limit: int = 365,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return daily NAV history, optionally filtered by date range."""
        rows = self._db.get_daily_nav(limit=limit)
        if not rows:
            return []

        def _in_range(d: str) -> bool:
            if start_date and d < start_date:
                return False
            if end_date and d > end_date:
                return False
            return True

        return [row for row in rows if _in_range(row["date"])]

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Return a simple portfolio summary based on latest NAV snapshot."""
        nav_history = self._db.get_daily_nav(limit=1)
        latest = nav_history[-1] if nav_history else None

        if not latest:
            # Fallback to zeroed portfolio when no NAV recorded yet
            return {
                "as_of": date.today().isoformat(),
                "total_value": 0.0,
                "cash": 0.0,
                "positions_value": 0.0,
                "daily_return": 0.0,
                "cumulative_return": 0.0,
            }

        return {
            "as_of": latest["date"],
            "total_value": latest["total_value"],
            "cash": latest["cash"],
            "positions_value": latest["positions_value"],
            "daily_return": latest.get("daily_return", 0.0),
            "cumulative_return": latest.get("cumulative_return", 0.0),
        }

