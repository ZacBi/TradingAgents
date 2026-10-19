from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from tradingagents.database import DatabaseManager
from tradingagents.database.models import RawMarketData, RawNews


class DatafeedService:
    """Simple datafeed service for historical and quasi-realtime data.

    For Phase 1 this is intentionally minimal: it surfaces recent rows from
    RawMarketData and RawNews as a unified list that the frontend can poll.
    Later phases can extend this to true realtime streaming and more sources.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def list_items(
        self,
        item_type: Optional[str] = None,
        ticker: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return a mixed list of datafeed items.

        item_type:
            - \"market\" for RawMarketData
            - \"news\" for RawNews
            - None for both
        """
        items: List[Dict[str, Any]] = []

        with self._db.session_scope() as session:  # type: ignore[attr-defined]
            if item_type in (None, "market"):
                stmt = select(RawMarketData).order_by(RawMarketData.fetched_at.desc()).limit(
                    limit
                )
                if ticker:
                    stmt = stmt.where(RawMarketData.ticker == ticker)
                rows = session.scalars(stmt).all()
                for row in rows:
                    items.append(
                        {
                            "type": "market",
                            "ticker": row.ticker,
                            "trade_date": row.trade_date,
                            "source": row.source,
                            "fetched_at": row.fetched_at.isoformat(),
                        }
                    )

            if item_type in (None, "news"):
                stmt = select(RawNews).order_by(RawNews.fetched_at.desc()).limit(limit)
                if ticker:
                    stmt = stmt.where(RawNews.ticker == ticker)
                rows = session.scalars(stmt).all()
                for row in rows:
                    items.append(
                        {
                            "type": "news",
                            "ticker": row.ticker,
                            "source": row.source,
                            "title": row.title,
                            "url": row.url,
                            "published_at": row.published_at,
                            "fetched_at": row.fetched_at.isoformat(),
                        }
                    )

        # Sort by fetched_at descending to mix types
        items.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
        return items[:limit]

