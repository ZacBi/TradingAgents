"""SQLAlchemy-based database manager for TradingAgents.

Provides CRUD operations using SQLAlchemy ORM.
Supports both SQLite (default) and PostgreSQL backends.
"""

import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    AgentDecision,
    Base,
    DailyNav,
    DecisionDataLink,
    Position,
    RawFundamentals,
    RawMarketData,
    RawNews,
    Trade,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations using SQLAlchemy ORM."""

    def __init__(self, db_path: str = "tradingagents.db"):
        """Initialize the database manager.

        Args:
            db_path: Path to SQLite database file, ":memory:" for in-memory,
                     or a PostgreSQL URL (postgresql://...).
        """
        self.db_path = db_path
        self._is_memory = db_path == ":memory:"
        self._is_postgres = db_path.startswith("postgresql://")

        # Build connection URL
        if self._is_postgres:
            url = db_path
        elif self._is_memory:
            url = "sqlite:///:memory:"
        else:
            # Ensure parent directory exists for file-based SQLite
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{db_path}"

        # Create engine with appropriate settings
        engine_kwargs = {}
        if not self._is_postgres and not self._is_memory:
            # SQLite WAL mode for better concurrency
            engine_kwargs["connect_args"] = {"check_same_thread": False}

        self.engine = create_engine(url, **engine_kwargs)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create all tables
        Base.metadata.create_all(self.engine)
        logger.info("Database initialized: %s", "PostgreSQL" if self._is_postgres else db_path)

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # agent_decisions
    # ------------------------------------------------------------------

    def save_decision(self, decision: Dict[str, Any]) -> int:
        """Insert a new agent decision and return its id.

        Expected keys: ticker, trade_date, final_decision, and optionally
        confidence, langfuse_trace_id, langfuse_trace_url, market_report,
        sentiment_report, news_report, fundamentals_report, valuation_result,
        debate_history, expert_opinions, risk_assessment.
        """
        with self.session_scope() as session:
            obj = AgentDecision(
                ticker=decision.get("ticker"),
                trade_date=decision.get("trade_date"),
                final_decision=decision.get("final_decision"),
                confidence=decision.get("confidence"),
                langfuse_trace_id=decision.get("langfuse_trace_id"),
                langfuse_trace_url=decision.get("langfuse_trace_url"),
                market_report=decision.get("market_report"),
                sentiment_report=decision.get("sentiment_report"),
                news_report=decision.get("news_report"),
                fundamentals_report=decision.get("fundamentals_report"),
                valuation_result=decision.get("valuation_result"),
                debate_history=decision.get("debate_history"),
                expert_opinions=decision.get("expert_opinions"),
                risk_assessment=decision.get("risk_assessment"),
            )
            session.add(obj)
            session.flush()
            return obj.id

    def get_decisions(
        self, ticker: Optional[str] = None, limit: int = 50
    ) -> List[dict]:
        """Retrieve recent decisions, optionally filtered by ticker."""
        with self.session_scope() as session:
            query = session.query(AgentDecision)
            if ticker:
                query = query.filter(AgentDecision.ticker == ticker)
            query = query.order_by(AgentDecision.created_at.desc()).limit(limit)
            return [self._model_to_dict(row) for row in query.all()]

    # ------------------------------------------------------------------
    # trades
    # ------------------------------------------------------------------

    def record_trade(self, trade: Dict[str, Any]) -> int:
        """Insert a trade record and return its id."""
        with self.session_scope() as session:
            obj = Trade(
                ticker=trade.get("ticker"),
                action=trade.get("action"),
                quantity=trade.get("quantity"),
                price=trade.get("price"),
                commission=trade.get("commission", 0),
                realized_pnl=trade.get("realized_pnl", 0),
                decision_id=trade.get("decision_id"),
            )
            session.add(obj)
            session.flush()
            return obj.id

    # ------------------------------------------------------------------
    # positions
    # ------------------------------------------------------------------

    def upsert_position(self, position: Dict[str, Any]) -> None:
        """Insert or update a position."""
        with self.session_scope() as session:
            ticker = position["ticker"]
            existing = session.query(Position).filter(Position.ticker == ticker).first()

            if existing:
                existing.quantity = position.get("quantity", 0)
                existing.avg_cost = position.get("avg_cost", 0)
                existing.current_price = position.get("current_price", 0)
                existing.unrealized_pnl = position.get("unrealized_pnl", 0)
            else:
                obj = Position(
                    ticker=ticker,
                    quantity=position.get("quantity", 0),
                    avg_cost=position.get("avg_cost", 0),
                    current_price=position.get("current_price", 0),
                    unrealized_pnl=position.get("unrealized_pnl", 0),
                )
                session.add(obj)

    def get_positions(self) -> List[dict]:
        """Get all open positions."""
        with self.session_scope() as session:
            positions = (
                session.query(Position).filter(Position.quantity != 0).all()
            )
            return [self._model_to_dict(p) for p in positions]

    # ------------------------------------------------------------------
    # daily_nav
    # ------------------------------------------------------------------

    def record_nav(self, nav: Dict[str, Any]) -> None:
        """Insert or replace daily NAV snapshot."""
        with self.session_scope() as session:
            date = nav["date"]
            existing = session.query(DailyNav).filter(DailyNav.date == date).first()

            if existing:
                existing.total_value = nav["total_value"]
                existing.cash = nav["cash"]
                existing.positions_value = nav["positions_value"]
                existing.daily_return = nav.get("daily_return", 0)
                existing.cumulative_return = nav.get("cumulative_return", 0)
            else:
                obj = DailyNav(
                    date=date,
                    total_value=nav["total_value"],
                    cash=nav["cash"],
                    positions_value=nav["positions_value"],
                    daily_return=nav.get("daily_return", 0),
                    cumulative_return=nav.get("cumulative_return", 0),
                )
                session.add(obj)

    # ------------------------------------------------------------------
    # Raw data archive helpers
    # ------------------------------------------------------------------

    def save_raw_market_data(self, data: Dict[str, Any]) -> int:
        """Archive raw market data and return its id."""
        with self.session_scope() as session:
            obj = RawMarketData(
                ticker=data["ticker"],
                trade_date=data["trade_date"],
                price_data_json=json.dumps(data.get("price_data")) if data.get("price_data") else None,
                indicators_json=json.dumps(data.get("indicators")) if data.get("indicators") else None,
                source=data.get("source", "yfinance"),
            )
            session.add(obj)
            session.flush()
            return obj.id

    def save_raw_news(self, data: Dict[str, Any]) -> int:
        """Archive raw news data and return its id."""
        with self.session_scope() as session:
            obj = RawNews(
                ticker=data.get("ticker"),
                source=data.get("source", "unknown"),
                title=data.get("title"),
                content=data.get("content"),
                url=data.get("url"),
                published_at=data.get("published_at"),
            )
            session.add(obj)
            session.flush()
            return obj.id

    def save_raw_fundamentals(self, data: Dict[str, Any]) -> int:
        """Archive raw fundamentals data and return its id."""
        with self.session_scope() as session:
            obj = RawFundamentals(
                ticker=data["ticker"],
                data_type=data.get("data_type", "info"),
                data_json=json.dumps(data.get("data")) if data.get("data") else None,
                source=data.get("source", "yfinance"),
                report_date=data.get("report_date"),
            )
            session.add(obj)
            session.flush()
            return obj.id

    # ------------------------------------------------------------------
    # Decision ↔ Raw data linking
    # ------------------------------------------------------------------

    def link_data_to_decision(
        self, decision_id: int, data_type: str, data_id: int
    ) -> None:
        """Create a link between a decision and a raw data record."""
        with self.session_scope() as session:
            obj = DecisionDataLink(
                decision_id=decision_id,
                data_type=data_type,
                data_id=data_id,
            )
            session.add(obj)

    def get_decision_data(self, decision_id: int) -> List[dict]:
        """Retrieve all raw data references for a given decision."""
        with self.session_scope() as session:
            links = (
                session.query(DecisionDataLink)
                .filter(DecisionDataLink.decision_id == decision_id)
                .all()
            )
            return [self._model_to_dict(link) for link in links]

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_dict(model_instance) -> dict:
        """Convert a SQLAlchemy model instance to a dictionary."""
        if model_instance is None:
            return {}
        return {
            c.name: getattr(model_instance, c.name)
            for c in model_instance.__table__.columns
        }
