"""Valuation data tools for LangChain agents.

Provides @tool decorated functions for:
- Earnings calendar dates
- Valuation metrics (P/E, P/B, EV/EBITDA, etc.)
- Institutional holders information
"""

from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_earnings_dates(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """
    Retrieve upcoming and historical earnings dates for a given ticker symbol.

    Use this tool to find when a company has reported or will report earnings,
    along with EPS estimates and actual results.

    Args:
        ticker (str): Ticker symbol of the company (e.g., "AAPL", "MSFT")

    Returns:
        str: CSV format with Date, EPS Estimate, Reported EPS, Surprise(%)
    """
    return route_to_vendor("get_earnings_dates", ticker)


@tool
def get_valuation_metrics(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """
    Retrieve comprehensive valuation metrics for a given ticker symbol.

    Use this tool to get key valuation ratios and metrics including:
    - P/E ratio (trailing and forward)
    - P/B ratio (Price to Book)
    - EV/EBITDA
    - PEG ratio
    - Price/Sales
    - Enterprise Value
    - Profitability margins (ROE, ROA, profit margin)
    - Dividend yield and payout ratio
    - Financial health metrics (debt/equity, current ratio)

    Args:
        ticker (str): Ticker symbol of the company (e.g., "AAPL", "MSFT")

    Returns:
        str: Formatted report containing valuation metrics
    """
    return route_to_vendor("get_valuation_metrics", ticker)


@tool
def get_institutional_holders(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """
    Retrieve institutional holders information for a given ticker symbol.

    Use this tool to find which institutions hold the stock and their positions.
    This is useful for understanding institutional sentiment and ownership concentration.

    Args:
        ticker (str): Ticker symbol of the company (e.g., "AAPL", "MSFT")

    Returns:
        str: CSV format with Holder name, Shares held, Date Reported, % Outstanding, Value
    """
    return route_to_vendor("get_institutional_holders", ticker)
