"""Raw data lineage: collect data_ids during a run and link to decisions."""

import logging
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# Context var: list of (data_type: str, data_id: int) collected during this run.
# Default None: use set_lineage_collector() to set a list for the current run.
_data_ids_ctx: ContextVar[list[tuple[str, int]] | None] = ContextVar(
    "lineage_data_ids", default=None
)


def set_lineage_collector(collector: list[tuple[str, int]] | None = None) -> list[tuple[str, int]]:
    """Set the list that will collect (data_type, data_id) for this run."""
    lst = collector if collector is not None else []
    _data_ids_ctx.set(lst)
    return lst


def get_data_ids() -> list[tuple[str, int]]:
    """Return the list of (data_type, data_id) collected so far."""
    val = _data_ids_ctx.get()
    return [] if val is None else list(val)


def append_data_id(data_type: str, data_id: int) -> None:
    """Append a (data_type, data_id) to the current run's collector."""
    lst = _data_ids_ctx.get()
    if lst is not None:
        lst.append((data_type, data_id))


def _get_db():
    """Get DatabaseManager from config or create one (cached by path)."""
    from tradingagents.dataflows.config import get_config
    config = get_config()
    if not config.get("database_enabled"):
        return None
    db = config.get("db")
    if db is not None:
        return db
    path = config.get("database_path", "tradingagents.db")
    if not hasattr(_get_db, "_cache"):
        _get_db._cache = {}
    if path not in _get_db._cache:
        from tradingagents.database import DatabaseManager
        _get_db._cache[path] = DatabaseManager(path)
    return _get_db._cache[path]


def try_record_raw_market_data(
    ticker: str,
    trade_date: str,
    price_data: Any = None,
    indicators: Any = None,
    source: str = "yfinance",
) -> None:
    """If DB is enabled, save raw market data and append (data_type, data_id) to lineage."""
    db = _get_db()
    if db is None:
        return
    try:
        payload = {
            "ticker": ticker,
            "trade_date": trade_date,
            "price_data": price_data,
            "indicators": indicators,
            "source": source,
        }
        data_id = db.save_raw_market_data(payload)
        append_data_id("raw_market_data", data_id)
        logger.debug("Lineage: saved raw_market_data id=%d", data_id)
    except Exception as e:
        logger.warning("Failed to record raw market data: %s", e)


def try_record_raw_news(
    ticker: str | None,
    source: str,
    title: str | None = None,
    content: str | None = None,
    url: str | None = None,
    published_at: str | None = None,
) -> None:
    """If DB is enabled, save raw news and append (data_type, data_id) to lineage."""
    db = _get_db()
    if db is None:
        return
    try:
        payload = {
            "ticker": ticker,
            "source": source,
            "title": title,
            "content": content,
            "url": url,
            "published_at": published_at,
        }
        data_id = db.save_raw_news(payload)
        append_data_id("raw_news", data_id)
        logger.debug("Lineage: saved raw_news id=%d", data_id)
    except Exception as e:
        logger.warning("Failed to record raw news: %s", e)


def try_record_raw_fundamentals(
    ticker: str,
    data_type: str,
    data: Any,
    source: str = "yfinance",
    report_date: str | None = None,
) -> None:
    """If DB is enabled, save raw fundamentals and append (data_type, data_id) to lineage."""
    db = _get_db()
    if db is None:
        return
    try:
        payload = {
            "ticker": ticker,
            "data_type": data_type,
            "data": data,
            "source": source,
            "report_date": report_date,
        }
        data_id = db.save_raw_fundamentals(payload)
        append_data_id("raw_fundamentals", data_id)
        logger.debug("Lineage: saved raw_fundamentals id=%d", data_id)
    except Exception as e:
        logger.warning("Failed to record raw fundamentals: %s", e)
