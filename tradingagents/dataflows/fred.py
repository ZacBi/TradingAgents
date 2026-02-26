"""FRED (Federal Reserve Economic Data) API integration.

Provides macroeconomic indicators:
- CPI (Consumer Price Index)
- GDP (Gross Domestic Product)
- Interest rates (Federal Funds, Treasury yields)
- Unemployment rate
- M2 money supply

Requires fredapi package (optional dependency) and FRED_API_KEY.
"""

import os
from datetime import datetime
from typing import Annotated, Optional

# Optional dependency
try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    Fred = None


# Cached Fred client instance
_fred_client: Optional["Fred"] = None


def _get_fred_client() -> "Fred":
    """Get or create a cached Fred client instance."""
    global _fred_client

    if not FRED_AVAILABLE:
        raise ImportError(
            "fredapi package not installed. "
            "Install with: uv pip install fredapi"
        )

    if _fred_client is None:
        # Try environment variable first, then config
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            from tradingagents.config import get_config
            api_key = get_config().get("fred_api_key")

        if not api_key:
            raise ValueError(
                "FRED API key not configured. "
                "Set FRED_API_KEY environment variable or config['fred_api_key']"
            )

        _fred_client = Fred(api_key=api_key)

    return _fred_client


# Common FRED series IDs
SERIES_IDS = {
    "cpi": "CPIAUCSL",           # Consumer Price Index for All Urban Consumers
    "gdp": "GDP",                # Gross Domestic Product
    "federal_funds": "FEDFUNDS", # Federal Funds Effective Rate
    "treasury_10y": "DGS10",     # 10-Year Treasury Constant Maturity Rate
    "treasury_2y": "DGS2",       # 2-Year Treasury Constant Maturity Rate
    "treasury_3m": "DTB3",       # 3-Month Treasury Bill Rate
    "unemployment": "UNRATE",    # Unemployment Rate
    "m2": "M2SL",               # M2 Money Stock
    "pce": "PCEPI",             # Personal Consumption Expenditures Price Index
    "core_pce": "PCEPILFE",     # Core PCE (excluding food and energy)
}


def get_fred_series(
    series_id: Annotated[str, "FRED series ID (e.g., CPIAUCSL, GDP, FEDFUNDS)"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Get a specific FRED data series.

    Args:
        series_id: FRED series identifier
        start_date: Start date for the data range
        end_date: End date for the data range

    Returns:
        CSV format with Date, Value columns
    """
    if not FRED_AVAILABLE:
        return (
            "Error: fredapi package not installed. "
            "Install with: uv pip install fredapi"
        )

    try:
        fred = _get_fred_client()
        data = fred.get_series(series_id, start_date, end_date)

        if data is None or data.empty:
            return f"No data found for series '{series_id}' between {start_date} and {end_date}"

        # Get series info for description
        try:
            info = fred.get_series_info(series_id)
            title = info.get("title", series_id)
            units = info.get("units", "")
            frequency = info.get("frequency", "")
        except Exception:
            title = series_id
            units = ""
            frequency = ""

        # Convert to DataFrame for CSV export
        import pandas as pd
        df = pd.DataFrame({"Date": data.index, "Value": data.values})
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

        csv_string = df.to_csv(index=False)

        header = f"# {title}\n"
        header += f"# Series ID: {series_id}\n"
        if units:
            header += f"# Units: {units}\n"
        if frequency:
            header += f"# Frequency: {frequency}\n"
        header += f"# Date range: {start_date} to {end_date}\n"
        header += f"# Total records: {len(df)}\n"
        header += f"# Retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return header + csv_string

    except Exception as e:
        return f"Error retrieving FRED series {series_id}: {str(e)}"


def get_cpi(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Get Consumer Price Index (CPI) data.

    CPI measures the average change in prices paid by urban consumers
    for a market basket of goods and services. Monthly frequency.

    Args:
        start_date: Start date for the data range
        end_date: End date for the data range

    Returns:
        CSV format with Date, Value columns
    """
    return get_fred_series(SERIES_IDS["cpi"], start_date, end_date)


def get_gdp(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Get Gross Domestic Product (GDP) data.

    GDP measures the total value of goods and services produced.
    Quarterly frequency, reported in billions of dollars.

    Args:
        start_date: Start date for the data range
        end_date: End date for the data range

    Returns:
        CSV format with Date, Value columns
    """
    return get_fred_series(SERIES_IDS["gdp"], start_date, end_date)


def get_interest_rate(
    rate_type: Annotated[str, "Rate type: federal_funds, treasury_10y, treasury_2y, treasury_3m"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Get interest rate data.

    Available rate types:
    - federal_funds: Federal Funds Effective Rate (daily)
    - treasury_10y: 10-Year Treasury Constant Maturity Rate (daily)
    - treasury_2y: 2-Year Treasury Constant Maturity Rate (daily)
    - treasury_3m: 3-Month Treasury Bill Rate (daily)

    Args:
        rate_type: Type of interest rate to retrieve
        start_date: Start date for the data range
        end_date: End date for the data range

    Returns:
        CSV format with Date, Value columns
    """
    rate_type = rate_type.lower()
    if rate_type not in SERIES_IDS:
        available = ["federal_funds", "treasury_10y", "treasury_2y", "treasury_3m"]
        return f"Error: Invalid rate_type '{rate_type}'. Available options: {available}"

    return get_fred_series(SERIES_IDS[rate_type], start_date, end_date)


def get_unemployment_rate(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Get unemployment rate data.

    The unemployment rate represents the number of unemployed as a
    percentage of the labor force. Monthly frequency.

    Args:
        start_date: Start date for the data range
        end_date: End date for the data range

    Returns:
        CSV format with Date, Value columns
    """
    return get_fred_series(SERIES_IDS["unemployment"], start_date, end_date)


def get_m2_money_supply(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Get M2 money supply data.

    M2 includes M1 plus savings deposits, money market securities,
    and other time deposits. Weekly/Monthly frequency.

    Args:
        start_date: Start date for the data range
        end_date: End date for the data range

    Returns:
        CSV format with Date, Value columns
    """
    return get_fred_series(SERIES_IDS["m2"], start_date, end_date)
