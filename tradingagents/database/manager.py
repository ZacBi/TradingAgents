"""Lightweight SQLite database manager for TradingAgents.

Provides CRUD helpers for the core tables defined in schema.py.
Uses Python's built-in sqlite3 — no external ORM dependency.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import SCHEMA_SQL


class DatabaseManager:
    """Manages a single SQLite database with the TradingAgents schema."""

    def __init__(self, db_path: str = "tradingagents.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    # ------------------------------------------------------------------
    # agent_decisions
    # ------------------------------------------------------------------

    def save_decision(self, decision: Dict[str, Any]) -> int:
        """Insert a new agent decision and return its id.

        Expected keys: ticker, trade_date, final_decision, and optionally
        confidence, market_report, sentiment_report, news_report,
        fundamentals_report, debate_history, expert_opinions, risk_assessment.
        """
        cols = [
            "ticker", "trade_date", "final_decision", "confidence",
            "market_report", "sentiment_report", "news_report",
            "fundamentals_report", "debate_history", "expert_opinions",
            "risk_assessment",
        ]
        values = [decision.get(c) for c in cols]
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(cols)

        with self._connect() as conn:
            cur = conn.execute(
                f"INSERT INTO agent_decisions ({col_names}) VALUES ({placeholders})",
                values,
            )
            return cur.lastrowid

    def get_decisions(
        self, ticker: Optional[str] = None, limit: int = 50
    ) -> List[dict]:
        """Retrieve recent decisions, optionally filtered by ticker."""
        query = "SELECT * FROM agent_decisions"
        params: list = []
        if ticker:
            query += " WHERE ticker = ?"
            params.append(ticker)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # trades
    # ------------------------------------------------------------------

    def record_trade(self, trade: Dict[str, Any]) -> int:
        """Insert a trade record and return its id."""
        # Only include keys that are actually provided; let SQLite
        # apply column defaults for omitted NOT-NULL-with-DEFAULT cols.
        allowed = {
            "ticker", "action", "quantity", "price",
            "commission", "realized_pnl", "decision_id",
        }
        cols = [c for c in allowed if trade.get(c) is not None]
        values = [trade[c] for c in cols]
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(cols)

        with self._connect() as conn:
            cur = conn.execute(
                f"INSERT INTO trades ({col_names}) VALUES ({placeholders})",
                values,
            )
            return cur.lastrowid

    # ------------------------------------------------------------------
    # positions
    # ------------------------------------------------------------------

    def upsert_position(self, position: Dict[str, Any]):
        """Insert or update a position."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO positions (ticker, quantity, avg_cost, current_price, unrealized_pnl, updated_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(ticker) DO UPDATE SET
                     quantity = excluded.quantity,
                     avg_cost = excluded.avg_cost,
                     current_price = excluded.current_price,
                     unrealized_pnl = excluded.unrealized_pnl,
                     updated_at = datetime('now')""",
                (
                    position["ticker"],
                    position.get("quantity", 0),
                    position.get("avg_cost", 0),
                    position.get("current_price", 0),
                    position.get("unrealized_pnl", 0),
                ),
            )

    def get_positions(self) -> List[dict]:
        """Get all open positions."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM positions WHERE quantity != 0"
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # daily_nav
    # ------------------------------------------------------------------

    def record_nav(self, nav: Dict[str, Any]):
        """Insert or replace daily NAV snapshot."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO daily_nav
                   (date, total_value, cash, positions_value, daily_return, cumulative_return)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    nav["date"],
                    nav["total_value"],
                    nav["cash"],
                    nav["positions_value"],
                    nav.get("daily_return", 0),
                    nav.get("cumulative_return", 0),
                ),
            )

    # ------------------------------------------------------------------
    # Raw data archive helpers
    # ------------------------------------------------------------------

    def save_raw_market_data(self, data: Dict[str, Any]) -> int:
        """Archive raw market data and return its id."""
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO raw_market_data (ticker, trade_date, price_data_json, indicators_json, source)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    data["ticker"],
                    data["trade_date"],
                    json.dumps(data.get("price_data")) if data.get("price_data") else None,
                    json.dumps(data.get("indicators")) if data.get("indicators") else None,
                    data.get("source", "yfinance"),
                ),
            )
            return cur.lastrowid

    def save_raw_news(self, data: Dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO raw_news (ticker, source, title, content, url, published_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    data.get("ticker"),
                    data.get("source", "unknown"),
                    data.get("title"),
                    data.get("content"),
                    data.get("url"),
                    data.get("published_at"),
                ),
            )
            return cur.lastrowid

    def save_raw_fundamentals(self, data: Dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO raw_fundamentals (ticker, data_type, data_json, source, report_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    data["ticker"],
                    data.get("data_type", "info"),
                    json.dumps(data.get("data")) if data.get("data") else None,
                    data.get("source", "yfinance"),
                    data.get("report_date"),
                ),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------
    # Decision ↔ Raw data linking
    # ------------------------------------------------------------------

    def link_data_to_decision(
        self, decision_id: int, data_type: str, data_id: int
    ):
        """Create a link between a decision and a raw data record."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO decision_data_links (decision_id, data_type, data_id) VALUES (?, ?, ?)",
                (decision_id, data_type, data_id),
            )

    def get_decision_data(self, decision_id: int) -> List[dict]:
        """Retrieve all raw data references for a given decision."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM decision_data_links WHERE decision_id = ?",
                (decision_id,),
            ).fetchall()
            return [dict(r) for r in rows]
