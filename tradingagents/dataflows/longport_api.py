"""Longport OpenAPI integration for real-time quotes and K-line data.

Provides:
- Real-time quote snapshots for US/HK/CN markets
- K-line (candlestick) data with multiple periods

Requires longport package (optional dependency) and Longport API credentials:
- LONGPORT_APP_KEY
- LONGPORT_APP_SECRET
- LONGPORT_ACCESS_TOKEN
"""

import os
from datetime import datetime
from typing import Annotated, Optional

# Optional dependency
try:
    from longport.openapi import AdjustType, Config, Period, QuoteContext
    LONGPORT_AVAILABLE = True
except ImportError:
    LONGPORT_AVAILABLE = False
    QuoteContext = None
    Config = None
    Period = None
    AdjustType = None


# Cached QuoteContext instance
_quote_context: Optional["QuoteContext"] = None


def _get_quote_context() -> "QuoteContext":
    """Get or create a cached QuoteContext instance."""
    global _quote_context

    if not LONGPORT_AVAILABLE:
        raise ImportError(
            "longport package not installed. "
            "Install with: uv pip install longport"
        )

    if _quote_context is None:
        # Try environment variables first, then config
        app_key = os.getenv("LONGPORT_APP_KEY")
        app_secret = os.getenv("LONGPORT_APP_SECRET")
        access_token = os.getenv("LONGPORT_ACCESS_TOKEN")

        if not all([app_key, app_secret, access_token]):
            from tradingagents.config import get_config
            config = get_config()
            app_key = app_key or config.get("longport_app_key")
            app_secret = app_secret or config.get("longport_app_secret")
            access_token = access_token or config.get("longport_access_token")

        if not all([app_key, app_secret, access_token]):
            raise ValueError(
                "Longport API credentials not configured. "
                "Set LONGPORT_APP_KEY, LONGPORT_APP_SECRET, LONGPORT_ACCESS_TOKEN "
                "environment variables or config keys."
            )

        lp_config = Config(
            app_key=app_key,
            app_secret=app_secret,
            access_token=access_token,
        )
        _quote_context = QuoteContext(lp_config)

    return _quote_context


def _normalize_symbol(symbol: str, market: str) -> str:
    """Normalize symbol format for Longport API.

    Args:
        symbol: Raw symbol (e.g., "AAPL", "700", "000001")
        market: Market code ("US", "HK", "CN")

    Returns:
        Longport-formatted symbol (e.g., "AAPL.US", "0700.HK", "000001.SZ")
    """
    symbol = symbol.upper().strip()
    market = market.upper().strip()

    # Remove existing suffix if present
    if "." in symbol:
        symbol = symbol.split(".")[0]

    if market == "US":
        return f"{symbol}.US"
    elif market == "HK":
        # Pad HK symbols to 4 digits
        symbol_num = symbol.lstrip("0")
        if symbol_num.isdigit():
            symbol = symbol_num.zfill(4)
        return f"{symbol}.HK"
    elif market in ("CN", "SH", "SZ"):
        # Determine exchange based on symbol prefix
        # 6xxxxx = Shanghai, 0xxxxx/3xxxxx = Shenzhen
        if symbol.startswith("6"):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"
    else:
        raise ValueError(f"Unknown market: {market}. Use 'US', 'HK', or 'CN'.")


# Period mapping
PERIOD_MAP = {
    "1min": "Min1",
    "5min": "Min5",
    "15min": "Min15",
    "30min": "Min30",
    "60min": "Min60",
    "day": "Day",
    "week": "Week",
    "month": "Month",
}


def get_longport_quote(
    symbol: Annotated[str, "Stock symbol (e.g., AAPL, 0700, 000001)"],
    market: Annotated[str, "Market code: US, HK, or CN"] = "US",
) -> str:
    """Get real-time quote snapshot for a symbol.

    Args:
        symbol: Stock symbol without exchange suffix
        market: Market code - "US" (United States), "HK" (Hong Kong), "CN" (China A-shares)

    Returns:
        Formatted quote data including last price, change, volume, etc.
    """
    if not LONGPORT_AVAILABLE:
        return (
            "Error: longport package not installed. "
            "Install with: uv pip install longport"
        )

    try:
        ctx = _get_quote_context()
        normalized = _normalize_symbol(symbol, market)

        quotes = ctx.quote([normalized])

        if not quotes:
            return f"No quote data found for symbol '{normalized}'"

        q = quotes[0]

        # Format the output
        lines = [
            f"# Real-time Quote for {normalized}",
            f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Symbol: {q.symbol}",
            f"Last Price: {q.last_done}",
            f"Previous Close: {q.prev_close}",
            f"Open: {q.open}",
            f"High: {q.high}",
            f"Low: {q.low}",
            f"Volume: {q.volume}",
            f"Turnover: {q.turnover}",
        ]

        # Calculate change
        if q.prev_close and q.last_done:
            change = float(q.last_done) - float(q.prev_close)
            change_pct = (change / float(q.prev_close)) * 100
            lines.append(f"Change: {change:.2f} ({change_pct:+.2f}%)")

        # Add timestamp if available
        if hasattr(q, "timestamp") and q.timestamp:
            lines.append(f"Timestamp: {q.timestamp}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error retrieving quote for {symbol} ({market}): {str(e)}"


def get_longport_kline(
    symbol: Annotated[str, "Stock symbol (e.g., AAPL, 0700, 000001)"],
    period: Annotated[str, "K-line period: 1min, 5min, 15min, 30min, 60min, day, week, month"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    market: Annotated[str, "Market code: US, HK, or CN"] = "US",
) -> str:
    """Get K-line (candlestick) data for a symbol.

    Args:
        symbol: Stock symbol without exchange suffix
        period: K-line period (1min, 5min, 15min, 30min, 60min, day, week, month)
        start_date: Start date for the data range (yyyy-mm-dd)
        end_date: End date for the data range (yyyy-mm-dd)
        market: Market code - "US", "HK", or "CN"

    Returns:
        CSV format with Date, Open, High, Low, Close, Volume columns
    """
    if not LONGPORT_AVAILABLE:
        return (
            "Error: longport package not installed. "
            "Install with: uv pip install longport"
        )

    period_lower = period.lower()
    if period_lower not in PERIOD_MAP:
        available = list(PERIOD_MAP.keys())
        return f"Error: Invalid period '{period}'. Available options: {available}"

    try:
        ctx = _get_quote_context()
        normalized = _normalize_symbol(symbol, market)

        # Convert period string to Longport Period enum
        period_enum = getattr(Period, PERIOD_MAP[period_lower])

        # Calculate approximate count based on date range
        # Longport API uses count instead of date range for candlesticks
        from datetime import datetime as dt
        start_dt = dt.strptime(start_date, "%Y-%m-%d")
        end_dt = dt.strptime(end_date, "%Y-%m-%d")
        days = (end_dt - start_dt).days + 1

        # Estimate count based on period
        if period_lower == "day":
            count = min(days, 1000)  # Max 1000 candles
        elif period_lower == "week":
            count = min(days // 7 + 1, 500)
        elif period_lower == "month":
            count = min(days // 30 + 1, 120)
        else:
            # Intraday: assume ~6.5 trading hours per day
            minutes_per_candle = int(period_lower.replace("min", "") or 60)
            candles_per_day = 390 // minutes_per_candle  # 390 minutes = 6.5 hours
            count = min(days * candles_per_day, 1000)

        candlesticks = ctx.candlesticks(
            normalized,
            period_enum,
            count,
            AdjustType.ForwardAdjust,
        )

        if not candlesticks:
            return f"No K-line data found for symbol '{normalized}' with period '{period}'"

        # Filter by date range and format as CSV
        csv_lines = ["Date,Open,High,Low,Close,Volume"]

        for candle in candlesticks:
            # Convert timestamp to date string
            if hasattr(candle, "timestamp"):
                candle_date = candle.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                candle_date = str(candle.time) if hasattr(candle, "time") else "N/A"

            csv_lines.append(
                f"{candle_date},{candle.open},{candle.high},{candle.low},{candle.close},{candle.volume}"
            )

        header = f"# K-line data for {normalized} ({period})\n"
        header += f"# Date range: {start_date} to {end_date}\n"
        header += f"# Total records: {len(candlesticks)}\n"
        header += f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + "\n".join(csv_lines)

    except Exception as e:
        return f"Error retrieving K-line for {symbol} ({market}): {str(e)}"
