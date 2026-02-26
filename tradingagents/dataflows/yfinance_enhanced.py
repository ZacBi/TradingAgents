"""YFinance enhanced data functions for valuation and institutional data.

Provides:
- Earnings calendar dates
- Valuation metrics (P/E, P/B, EV/EBITDA, etc.)
- Institutional holders information
"""

from datetime import datetime
from typing import Annotated

import yfinance as yf


def get_earnings_dates(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """Get upcoming and historical earnings dates for a ticker.

    Returns CSV format with Date, EPS Estimate, Reported EPS, Surprise(%).
    """
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        earnings = ticker_obj.earnings_dates

        if earnings is None or earnings.empty:
            return f"No earnings dates found for symbol '{ticker}'"

        # Reset index to make date a column
        earnings = earnings.reset_index()

        # Rename columns for clarity
        earnings.columns = [
            col.replace(" ", "_") for col in earnings.columns
        ]

        csv_string = earnings.to_csv(index=False)

        header = f"# Earnings Dates for {ticker.upper()}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"# Total records: {len(earnings)}\n\n"

        return header + csv_string

    except Exception as e:
        return f"Error retrieving earnings dates for {ticker}: {str(e)}"


def get_valuation_metrics(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """Get comprehensive valuation metrics for a ticker.

    Extracts P/E, P/B, EV/EBITDA, PEG, Price/Sales, Price/FCF and other
    valuation-related fields from yfinance info.
    """
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        info = ticker_obj.info

        if not info:
            return f"No valuation data found for symbol '{ticker}'"

        # Valuation metrics fields
        valuation_fields = [
            ("Company", info.get("longName")),
            ("Sector", info.get("sector")),
            ("Industry", info.get("industry")),
            # Price metrics
            ("Current Price", info.get("currentPrice")),
            ("Previous Close", info.get("previousClose")),
            ("52 Week High", info.get("fiftyTwoWeekHigh")),
            ("52 Week Low", info.get("fiftyTwoWeekLow")),
            # Valuation ratios
            ("Market Cap", info.get("marketCap")),
            ("Enterprise Value", info.get("enterpriseValue")),
            ("P/E Ratio (Trailing)", info.get("trailingPE")),
            ("P/E Ratio (Forward)", info.get("forwardPE")),
            ("PEG Ratio", info.get("pegRatio")),
            ("Price to Book", info.get("priceToBook")),
            ("Price to Sales (TTM)", info.get("priceToSalesTrailing12Months")),
            ("EV/Revenue", info.get("enterpriseToRevenue")),
            ("EV/EBITDA", info.get("enterpriseToEbitda")),
            # Per share metrics
            ("EPS (Trailing)", info.get("trailingEps")),
            ("EPS (Forward)", info.get("forwardEps")),
            ("Book Value Per Share", info.get("bookValue")),
            # Profitability
            ("Profit Margin", info.get("profitMargins")),
            ("Operating Margin", info.get("operatingMargins")),
            ("ROE", info.get("returnOnEquity")),
            ("ROA", info.get("returnOnAssets")),
            ("ROIC", info.get("returnOnCapital")),
            # Growth
            ("Revenue Growth (YoY)", info.get("revenueGrowth")),
            ("Earnings Growth (YoY)", info.get("earningsGrowth")),
            # Dividend
            ("Dividend Rate", info.get("dividendRate")),
            ("Dividend Yield", info.get("dividendYield")),
            ("Payout Ratio", info.get("payoutRatio")),
            # Financial health
            ("Debt to Equity", info.get("debtToEquity")),
            ("Current Ratio", info.get("currentRatio")),
            ("Quick Ratio", info.get("quickRatio")),
            # Cash flow
            ("Free Cash Flow", info.get("freeCashflow")),
            ("Operating Cash Flow", info.get("operatingCashflow")),
        ]

        lines = []
        for label, value in valuation_fields:
            if value is not None:
                # Format large numbers
                if isinstance(value, (int, float)) and abs(value) >= 1e9:
                    formatted = f"{value/1e9:.2f}B"
                elif isinstance(value, (int, float)) and abs(value) >= 1e6:
                    formatted = f"{value/1e6:.2f}M"
                elif isinstance(value, float):
                    formatted = f"{value:.4f}"
                else:
                    formatted = str(value)
                lines.append(f"{label}: {formatted}")

        header = f"# Valuation Metrics for {ticker.upper()}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + "\n".join(lines)

    except Exception as e:
        return f"Error retrieving valuation metrics for {ticker}: {str(e)}"


def get_institutional_holders(
    ticker: Annotated[str, "ticker symbol of the company"],
) -> str:
    """Get institutional holders information for a ticker.

    Returns CSV format with Holder, Shares, Date Reported, % Out, Value.
    """
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        holders = ticker_obj.institutional_holders

        if holders is None or holders.empty:
            return f"No institutional holders data found for symbol '{ticker}'"

        csv_string = holders.to_csv(index=False)

        header = f"# Institutional Holders for {ticker.upper()}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"# Total institutions: {len(holders)}\n\n"

        return header + csv_string

    except Exception as e:
        return f"Error retrieving institutional holders for {ticker}: {str(e)}"
