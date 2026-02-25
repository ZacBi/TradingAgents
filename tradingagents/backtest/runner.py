"""Backtest runner: load decisions, fetch price data, run Backtrader, return metrics."""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import backtrader as bt
import pandas as pd

from .strategy import AgentDecisionStrategy

logger = logging.getLogger(__name__)


def _load_decisions_from_db(
    db_path: str,
    ticker: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """Load decisions from SQLite via DatabaseManager."""
    from tradingagents.database import DatabaseManager

    db = DatabaseManager(db_path)
    return db.get_decisions_in_range(ticker, start_date, end_date)


def _load_decisions_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Load decisions from CSV with columns: ticker, trade_date, final_decision."""
    rows: List[Dict[str, Any]] = []
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "ticker": row.get("ticker", "").strip(),
                "trade_date": row.get("trade_date", "").strip(),
                "final_decision": row.get("final_decision", "HOLD").strip().upper(),
            })
    return rows


def _decisions_to_map(decisions: List[Dict[str, Any]], ticker: Optional[str] = None) -> Dict[str, str]:
    """Build date -> BUY|SELL|HOLD map. If ticker is set, filter by ticker."""
    out: Dict[str, str] = {}
    for d in decisions:
        t = (d.get("ticker") or "").strip().upper()
        if ticker and t != ticker.upper():
            continue
        date_str = (d.get("trade_date") or "").strip()
        if not date_str:
            continue
        decision = (d.get("final_decision") or "HOLD").strip().upper()
        if decision not in ("BUY", "SELL", "HOLD"):
            decision = "HOLD"
        out[date_str] = decision
    return out


def _fetch_prices(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch OHLCV from yfinance and return DataFrame with lowercase columns for Backtrader."""
    import yfinance as yf

    sym = ticker.upper()
    obj = yf.Ticker(sym)
    df = obj.history(start=start_date, end=end_date)
    if df.empty or len(df) < 2:
        raise ValueError(f"Insufficient price data for {sym} between {start_date} and {end_date}")
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })
    return df[["open", "high", "low", "close", "volume"]]


def run_backtest(
    ticker: str,
    start_date: str,
    end_date: str,
    decisions: Optional[Dict[str, str]] = None,
    decisions_from_db: Optional[str] = None,
    decisions_from_csv: Optional[str] = None,
    allocation: float = 1.0,
) -> Dict[str, Any]:
    """Run backtest and return metrics.

    Either pass `decisions` (date -> BUY|SELL|HOLD) directly, or load from DB or CSV.
    If both decisions_from_db and decisions_from_csv are None and decisions is None,
    will try decisions_from_db with default db path.

    Returns:
        dict with keys: total_return, annual_return, sharpe_ratio, max_drawdown, max_drawdown_pct,
        win_rate, num_trades, num_bars.
    """
    if decisions is None and decisions_from_csv:
        raw = _load_decisions_from_csv(decisions_from_csv)
        decisions = _decisions_to_map(raw, ticker)
    elif decisions is None and decisions_from_db:
        raw = _load_decisions_from_db(decisions_from_db, ticker, start_date, end_date)
        decisions = _decisions_to_map(raw, ticker)
    if decisions is None:
        decisions = {}

    df = _fetch_prices(ticker, start_date, end_date)
    num_bars = len(df)

    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(AgentDecisionStrategy, decisions=decisions, allocation=allocation)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    end_value = cerebro.broker.getvalue()

    # Basic metrics
    total_return = (end_value - start_value) / start_value if start_value else 0.0
    num_years = max(num_bars / 252.0, 1e-6)
    annual_return = (1.0 + total_return) ** (1.0 / num_years) - 1.0 if total_return > -1 else -1.0

    sharpe_ratio = None
    max_drawdown = None
    max_drawdown_pct = None
    win_rate = None
    num_trades = 0

    try:
        strat = results[0]
        if hasattr(strat.analyzers.drawdown, "get_analysis"):
            dd = strat.analyzers.drawdown.get_analysis()
            max_dd = dd.get("max", {})
            max_drawdown = max_dd.get("drawdown")
            if max_drawdown is not None and start_value:
                max_drawdown_pct = max_drawdown / start_value
        if hasattr(strat.analyzers.sharpe, "get_analysis"):
            sharpe_ratio = strat.analyzers.sharpe.get_analysis().get("sharperatio")
        if hasattr(strat.analyzers.trades, "get_analysis"):
            ta = strat.analyzers.trades.get_analysis()
            total_closed = ta.get("total", {}).get("closed", 0) or 0
            won = ta.get("won", {}).get("total", 0) or 0
            num_trades = total_closed
            win_rate = (won / total_closed) if total_closed else None
    except Exception as e:
        logger.warning("Analyzers failed: %s", e)

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate": win_rate,
        "num_trades": num_trades,
        "num_bars": num_bars,
        "start_value": start_value,
        "end_value": end_value,
    }
