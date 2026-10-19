from __future__ import annotations

from typing import Any, Dict, List, Optional

from tradingagents.database import DatabaseManager


class DecisionService:
    """Read-only decision access helpers built on DatabaseManager."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def list_decisions(
        self,
        ticker: Optional[str] = None,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent decisions, optionally filtered by ticker/date."""
        if start_date and end_date and ticker:
            rows = self._db.get_decisions_in_range(
                ticker=ticker, start_date=start_date, end_date=end_date
            )
        else:
            rows = self._db.get_decisions(ticker=ticker, limit=limit)

        def _in_range(row: Dict[str, Any]) -> bool:
            trade_date = row.get("trade_date")
            if start_date and trade_date < start_date:
                return False
            if end_date and trade_date > end_date:
                return False
            return True

        if start_date or end_date:
            rows = [r for r in rows if _in_range(r)]
        return rows

    def get_decision(self, decision_id: int) -> Optional[Dict[str, Any]]:
        """Return a single decision with its linked raw data references."""
        # DatabaseManager does not expose a direct get_decision(id), so we query via session.
        # To avoid leaking SQLAlchemy details, we re-use the internal _model_to_dict helper.
        with self._db.session_scope() as session:  # type: ignore[attr-defined]
            from sqlalchemy import select
            from tradingagents.database.models import AgentDecision  # type: ignore

            stmt = select(AgentDecision).where(AgentDecision.id == decision_id)
            row = session.scalars(stmt).first()
            if not row:
                return None
            decision_dict = self._db._model_to_dict(row)  # type: ignore[attr-defined]

        # Attach data_links via existing helper
        decision_dict["data_links"] = self._db.get_decision_data(decision_id)
        return decision_dict

