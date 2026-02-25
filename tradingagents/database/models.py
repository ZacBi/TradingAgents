"""SQLAlchemy ORM models for TradingAgents persistence layer.

Defines all database models using SQLAlchemy 2.0 declarative syntax.
These models correspond to the tables defined in schema.py.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# ============================================================
# Portfolio Management
# ============================================================


class Position(Base):
    """Current portfolio positions."""

    __tablename__ = "positions"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    current_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


class Trade(Base):
    """Trade execution records."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)  # BUY / SELL
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    commission: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    decision_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("agent_decisions.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    # Relationship
    decision: Mapped[Optional["AgentDecision"]] = relationship(
        "AgentDecision", back_populates="trades"
    )


class DailyNav(Base):
    """Daily net asset value snapshots."""

    __tablename__ = "daily_nav"

    date: Mapped[str] = mapped_column(String, primary_key=True)  # YYYY-MM-DD
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    positions_value: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cumulative_return: Mapped[float] = mapped_column(Float, nullable=False, default=0)


# ============================================================
# Decision Audit Trail
# ============================================================


class AgentDecision(Base):
    """Agent decision records with full audit trail."""

    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    trade_date: Mapped[str] = mapped_column(String, nullable=False)
    final_decision: Mapped[str] = mapped_column(String, nullable=False)  # BUY/SELL/HOLD
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    langfuse_trace_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    langfuse_trace_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    market_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sentiment_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    news_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fundamentals_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valuation_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    debate_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expert_opinions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_assessment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    # Relationships
    trades: Mapped[list["Trade"]] = relationship(
        "Trade", back_populates="decision", cascade="all, delete-orphan"
    )
    data_links: Mapped[list["DecisionDataLink"]] = relationship(
        "DecisionDataLink", back_populates="decision", cascade="all, delete-orphan"
    )

    # Composite index for common queries
    __table_args__ = (Index("idx_decisions_ticker_date", "ticker", "trade_date"),)


class DecisionDataLink(Base):
    """Links between decisions and raw data records."""

    __tablename__ = "decision_data_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent_decisions.id"), nullable=False, index=True
    )
    data_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # market_data / news / sentiment / fundamentals / deep_research / macro
    data_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationship
    decision: Mapped["AgentDecision"] = relationship(
        "AgentDecision", back_populates="data_links"
    )


# ============================================================
# Raw Data Archive
# ============================================================


class RawMarketData(Base):
    """Archived raw market data."""

    __tablename__ = "raw_market_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    trade_date: Mapped[str] = mapped_column(String, nullable=False)
    price_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    indicators_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="yfinance")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    __table_args__ = (Index("idx_raw_market_ticker", "ticker", "trade_date"),)


class RawNews(Base):
    """Archived news articles."""

    __tablename__ = "raw_news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    published_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )


class RawSocialSentiment(Base):
    """Archived social media sentiment data."""

    __tablename__ = "raw_social_sentiment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    raw_posts_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    target_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )


class RawFundamentals(Base):
    """Archived fundamental data."""

    __tablename__ = "raw_fundamentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False, index=True)
    data_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # balance_sheet / cashflow / income_statement / info
    data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="yfinance")
    report_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )


class RawDeepResearch(Base):
    """Archived deep research reports."""

    __tablename__ = "raw_deep_research"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sources_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trigger_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)
    started_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    completed_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class RawMacroData(Base):
    """Archived macroeconomic data."""

    __tablename__ = "raw_macro_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observation_date: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="fred")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
