from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from tradingagents.api.dependencies import get_db_manager
from tradingagents.database import DatabaseManager
from tradingagents.services.datafeed import DatafeedService


router = APIRouter()


def get_datafeed_service(db: DatabaseManager = Depends(get_db_manager)) -> DatafeedService:
    return DatafeedService(db)


@router.get("/datafeed")
def list_datafeed_items(
    service: DatafeedService = Depends(get_datafeed_service),
    type: Optional[str] = Query(
        None,
        description="Filter by item type: 'market' or 'news'",
        regex="^(market|news)$",
    ),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    limit: int = Query(100, ge=1, le=500),
):
    """List recent datafeed items (market data and news)."""
    return service.list_items(item_type=type, ticker=ticker, limit=limit)

