from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from tradingagents.api.dependencies import get_db_manager
from tradingagents.database import DatabaseManager
from tradingagents.services.decisions import DecisionService


router = APIRouter()


def get_decision_service(db: DatabaseManager = Depends(get_db_manager)) -> DecisionService:
    return DecisionService(db)


@router.get("/decisions")
def list_decisions(
    service: DecisionService = Depends(get_decision_service),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    limit: int = Query(50, ge=1, le=500),
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
):
    """List recent decisions, optionally filtered by ticker and/or date range."""
    return service.list_decisions(
        ticker=ticker, limit=limit, start_date=start_date, end_date=end_date
    )


@router.get("/decisions/{decision_id}")
def get_decision(
    decision_id: int = Path(..., description="AgentDecision.id"),
    service: DecisionService = Depends(get_decision_service),
):
    """Get a single decision with its linked raw data references."""
    decision = service.get_decision(decision_id)
    if decision is None:
        # FastAPI will serialize this as a 200 with null if we return None,
        # but for now keep it simple; detailed error model can be added later.
        return {}
    return decision

