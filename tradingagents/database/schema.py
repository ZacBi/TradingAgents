"""SQL schema definitions for TradingAgents persistence layer.

All tables live in a single SQLite database.  The schema covers:
  - Portfolio management (positions, trades, daily_nav)
  - Decision audit trail (agent_decisions, decision_data_links)
  - Raw data archive (raw_market_data, raw_news, raw_social_sentiment,
    raw_fundamentals, raw_deep_research, raw_macro_data)
"""

SCHEMA_SQL = """
-- ============================================================
-- Portfolio Management
-- ============================================================

CREATE TABLE IF NOT EXISTS positions (
    ticker          TEXT PRIMARY KEY,
    quantity        REAL NOT NULL DEFAULT 0,
    avg_cost        REAL NOT NULL DEFAULT 0,
    current_price   REAL NOT NULL DEFAULT 0,
    unrealized_pnl  REAL NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    action          TEXT NOT NULL,           -- BUY / SELL
    quantity        REAL NOT NULL,
    price           REAL NOT NULL,
    commission      REAL NOT NULL DEFAULT 0,
    realized_pnl    REAL NOT NULL DEFAULT 0,
    decision_id     INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (decision_id) REFERENCES agent_decisions(id)
);

CREATE TABLE IF NOT EXISTS daily_nav (
    date            TEXT PRIMARY KEY,        -- YYYY-MM-DD
    total_value     REAL NOT NULL,
    cash            REAL NOT NULL,
    positions_value REAL NOT NULL,
    daily_return    REAL NOT NULL DEFAULT 0,
    cumulative_return REAL NOT NULL DEFAULT 0
);

-- ============================================================
-- Decision Audit Trail
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_decisions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT NOT NULL,
    trade_date          TEXT NOT NULL,
    final_decision      TEXT NOT NULL,       -- BUY / SELL / HOLD
    confidence          REAL,
    langfuse_trace_id   TEXT,
    langfuse_trace_url  TEXT,
    market_report       TEXT,
    sentiment_report    TEXT,
    news_report         TEXT,
    fundamentals_report TEXT,
    debate_history      TEXT,
    expert_opinions     TEXT,
    risk_assessment     TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decision_data_links (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id     INTEGER NOT NULL,
    data_type       TEXT NOT NULL,            -- market_data / news / sentiment / fundamentals / deep_research / macro
    data_id         INTEGER NOT NULL,
    FOREIGN KEY (decision_id) REFERENCES agent_decisions(id)
);

-- ============================================================
-- Raw Data Archive
-- ============================================================

CREATE TABLE IF NOT EXISTS raw_market_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    price_data_json TEXT,
    indicators_json TEXT,
    source          TEXT NOT NULL DEFAULT 'yfinance',
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS raw_news (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT,
    source          TEXT NOT NULL,
    title           TEXT,
    content         TEXT,
    url             TEXT,
    published_at    TEXT,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS raw_social_sentiment (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    platform        TEXT NOT NULL,
    raw_posts_json  TEXT,
    sentiment_score REAL,
    post_count      INTEGER DEFAULT 0,
    target_date     TEXT,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS raw_fundamentals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    data_type       TEXT NOT NULL,            -- balance_sheet / cashflow / income_statement / info
    data_json       TEXT,
    source          TEXT NOT NULL DEFAULT 'yfinance',
    report_date     TEXT,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS raw_deep_research (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    query           TEXT,
    report_markdown TEXT,
    sources_json    TEXT,
    trigger_reason  TEXT,
    tokens_used     INTEGER DEFAULT 0,
    cost            REAL DEFAULT 0,
    started_at      TEXT,
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS raw_macro_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator       TEXT NOT NULL,
    value           REAL,
    observation_date TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'fred',
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- Indexes for common queries
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_decision ON trades(decision_id);
CREATE INDEX IF NOT EXISTS idx_decisions_ticker_date ON agent_decisions(ticker, trade_date);
CREATE INDEX IF NOT EXISTS idx_links_decision ON decision_data_links(decision_id);
CREATE INDEX IF NOT EXISTS idx_raw_market_ticker ON raw_market_data(ticker, trade_date);
CREATE INDEX IF NOT EXISTS idx_raw_news_ticker ON raw_news(ticker);
CREATE INDEX IF NOT EXISTS idx_raw_fundamentals_ticker ON raw_fundamentals(ticker);
"""
