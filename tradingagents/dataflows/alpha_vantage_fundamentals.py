from .alpha_vantage_common import _make_api_request


def get_fundamentals(ticker: str, curr_date: str = None) -> str:
    """
    Retrieve comprehensive fundamental data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Company overview data including financial ratios and key metrics
    """
    params = {
        "symbol": ticker,
    }

    result = _make_api_request("OVERVIEW", params)
    
    # Lineage: record raw fundamentals data when DB is enabled
    try:
        from tradingagents.graph.lineage import try_record_raw_fundamentals
        try_record_raw_fundamentals(
            ticker=ticker,
            data_type="overview",
            data=result,
            source="alpha_vantage",
            report_date=curr_date,
        )
    except Exception:
        pass
    
    return result


def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """
    Retrieve balance sheet data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Balance sheet data with normalized fields
    """
    params = {
        "symbol": ticker,
    }

    result = _make_api_request("BALANCE_SHEET", params)
    
    # Lineage: record raw fundamentals data when DB is enabled
    try:
        from tradingagents.graph.lineage import try_record_raw_fundamentals
        try_record_raw_fundamentals(
            ticker=ticker,
            data_type="balance_sheet",
            data=result,
            source="alpha_vantage",
            report_date=curr_date,
        )
    except Exception:
        pass
    
    return result


def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """
    Retrieve cash flow statement data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Cash flow statement data with normalized fields
    """
    params = {
        "symbol": ticker,
    }

    result = _make_api_request("CASH_FLOW", params)
    
    # Lineage: record raw fundamentals data when DB is enabled
    try:
        from tradingagents.graph.lineage import try_record_raw_fundamentals
        try_record_raw_fundamentals(
            ticker=ticker,
            data_type="cashflow",
            data=result,
            source="alpha_vantage",
            report_date=curr_date,
        )
    except Exception:
        pass
    
    return result


def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """
    Retrieve income statement data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Income statement data with normalized fields
    """
    params = {
        "symbol": ticker,
    }

    result = _make_api_request("INCOME_STATEMENT", params)
    
    # Lineage: record raw fundamentals data when DB is enabled
    try:
        from tradingagents.graph.lineage import try_record_raw_fundamentals
        try_record_raw_fundamentals(
            ticker=ticker,
            data_type="income_statement",
            data=result,
            source="alpha_vantage",
            report_date=curr_date,
        )
    except Exception:
        pass
    
    return result

