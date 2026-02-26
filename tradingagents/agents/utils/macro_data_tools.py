"""Macroeconomic data tools for LangChain agents.

Provides @tool decorated functions for FRED data:
- CPI (Consumer Price Index)
- GDP (Gross Domestic Product)
- Interest rates (Federal Funds, Treasury yields)
- Unemployment rate
- M2 money supply

Requires fredapi package and FRED_API_KEY environment variable.
"""

from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_cpi_data(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve Consumer Price Index (CPI) data from FRED.

    CPI measures the average change in prices paid by urban consumers
    for a market basket of goods and services. Use this to understand
    inflation trends.

    Note: Data is released monthly, typically with a 2-week lag.

    Args:
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format

    Returns:
        str: CSV format with Date, Value columns
    """
    return route_to_vendor("get_cpi_data", start_date, end_date)


@tool
def get_gdp_data(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve Gross Domestic Product (GDP) data from FRED.

    GDP measures the total value of goods and services produced in
    the economy. Use this to understand overall economic growth.

    Note: Data is released quarterly, with preliminary and revised estimates.

    Args:
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format

    Returns:
        str: CSV format with Date, Value (in billions of dollars) columns
    """
    return route_to_vendor("get_gdp_data", start_date, end_date)


@tool
def get_interest_rate_data(
    rate_type: Annotated[str, "Rate type: federal_funds, treasury_10y, treasury_2y, treasury_3m"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve interest rate data from FRED.

    Available rate types:
    - federal_funds: Federal Funds Effective Rate (overnight lending rate)
    - treasury_10y: 10-Year Treasury yield (benchmark for mortgages)
    - treasury_2y: 2-Year Treasury yield (sensitive to Fed policy)
    - treasury_3m: 3-Month Treasury Bill rate (short-term benchmark)

    Use this to understand monetary policy and bond market conditions.
    The spread between 10y and 2y is a recession indicator (inverted yield curve).

    Args:
        rate_type (str): Type of interest rate to retrieve
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format

    Returns:
        str: CSV format with Date, Value (percentage) columns
    """
    return route_to_vendor("get_interest_rate_data", rate_type, start_date, end_date)


@tool
def get_unemployment_data(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve unemployment rate data from FRED.

    The unemployment rate represents the number of unemployed as a
    percentage of the labor force. Use this to understand labor
    market conditions.

    Note: Data is released monthly (first Friday of the month).

    Args:
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format

    Returns:
        str: CSV format with Date, Value (percentage) columns
    """
    return route_to_vendor("get_unemployment_data", start_date, end_date)


@tool
def get_m2_data(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve M2 money supply data from FRED.

    M2 includes M1 (cash and checking deposits) plus savings deposits,
    money market securities, and other time deposits. Use this to
    understand monetary conditions and liquidity in the economy.

    Rapid M2 growth can signal future inflation.

    Args:
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format

    Returns:
        str: CSV format with Date, Value (in billions of dollars) columns
    """
    return route_to_vendor("get_m2_data", start_date, end_date)
