"""Real-time market data tools for LangChain agents.

Provides @tool decorated functions for:
- Real-time quote snapshots (US/HK/CN markets)
- K-line (candlestick) data with multiple periods

Requires longport package and Longport API credentials.
"""

from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_realtime_quote(
    symbol: Annotated[str, "Stock symbol (e.g., AAPL, 0700, 000001)"],
    market: Annotated[str, "Market code: US, HK, or CN"] = "US",
) -> str:
    """
    Retrieve real-time quote snapshot for a stock.

    Provides current market data including:
    - Last traded price
    - Open/High/Low/Close
    - Volume and turnover
    - Price change and percentage

    Supports multiple markets:
    - US: United States stocks (e.g., AAPL, MSFT, TSLA)
    - HK: Hong Kong stocks (e.g., 0700 for Tencent, 9988 for Alibaba)
    - CN: China A-shares (e.g., 000001 for Ping An, 600519 for Moutai)

    Note: Requires Longport API credentials (LONGPORT_APP_KEY, LONGPORT_APP_SECRET, 
    LONGPORT_ACCESS_TOKEN).

    Args:
        symbol (str): Stock symbol without exchange suffix
        market (str): Market code - "US", "HK", or "CN" (default: "US")

    Returns:
        str: Formatted quote data with price, volume, and change information
    """
    return route_to_vendor("get_realtime_quote", symbol, market)


@tool
def get_kline_data(
    symbol: Annotated[str, "Stock symbol (e.g., AAPL, 0700, 000001)"],
    period: Annotated[str, "K-line period: 1min, 5min, 15min, 30min, 60min, day, week, month"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    market: Annotated[str, "Market code: US, HK, or CN"] = "US",
) -> str:
    """
    Retrieve K-line (candlestick) data for a stock.

    Provides OHLCV (Open, High, Low, Close, Volume) data at various time intervals.

    Available periods:
    - Intraday: 1min, 5min, 15min, 30min, 60min
    - Daily and longer: day, week, month

    Supports multiple markets:
    - US: United States stocks
    - HK: Hong Kong stocks
    - CN: China A-shares

    Use this for technical analysis, charting, and pattern recognition.

    Note: Requires Longport API credentials.

    Args:
        symbol (str): Stock symbol without exchange suffix
        period (str): K-line period (1min, 5min, 15min, 30min, 60min, day, week, month)
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
        market (str): Market code - "US", "HK", or "CN" (default: "US")

    Returns:
        str: CSV format with Date, Open, High, Low, Close, Volume columns
    """
    return route_to_vendor("get_kline_data", symbol, period, start_date, end_date, market)
