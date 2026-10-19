from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from tradingagents.api.dependencies import get_db_manager
from tradingagents.database import DatabaseManager
from tradingagents.services.portfolio import PortfolioService


router = APIRouter()


def get_portfolio_service(db: DatabaseManager = Depends(get_db_manager)) -> PortfolioService:
    return PortfolioService(db)


@router.get("/portfolio")
def read_portfolio_summary(service: PortfolioService = Depends(get_portfolio_service)):
    """Get portfolio summary based on latest NAV snapshot."""
    return service.get_portfolio_summary()


@router.get("/positions")
def read_positions(service: PortfolioService = Depends(get_portfolio_service)):
    """Get all open positions."""
    return service.get_positions()


@router.get("/nav")
def read_nav_history(
    service: PortfolioService = Depends(get_portfolio_service),
    limit: int = Query(365, ge=1, le=3650),
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
):
    """Get NAV history for charts."""
    return service.get_nav_history(limit=limit, start_date=start_date, end_date=end_date)

