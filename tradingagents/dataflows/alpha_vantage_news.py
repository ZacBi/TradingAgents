from .alpha_vantage_common import _make_api_request, format_datetime_for_api


def get_news(ticker, start_date, end_date) -> dict[str, str] | str:
    """Returns live and historical market news & sentiment data from premier news outlets worldwide.

    Covers stocks, cryptocurrencies, forex, and topics like fiscal policy, mergers & acquisitions, IPOs.

    Args:
        ticker: Stock symbol for news articles.
        start_date: Start date for news search.
        end_date: End date for news search.

    Returns:
        Dictionary containing news sentiment data or JSON string.
    """

    params = {
        "tickers": ticker,
        "time_from": format_datetime_for_api(start_date),
        "time_to": format_datetime_for_api(end_date),
    }

    result = _make_api_request("NEWS_SENTIMENT", params)
    
    # Lineage: record raw news data when DB is enabled
    try:
        from tradingagents.graph.lineage import try_record_raw_news
        # Parse result if it's a dict, extract news items
        if isinstance(result, dict) and "feed" in result:
            for item in result.get("feed", [])[:50]:  # Limit to 50 items
                try_record_raw_news(
                    ticker=ticker,
                    source="alpha_vantage",
                    title=item.get("title"),
                    content=item.get("summary"),
                    url=item.get("url"),
                    published_at=item.get("time_published"),
                )
        elif isinstance(result, str):
            # If it's a string, try to record it as a single news item
            try_record_raw_news(
                ticker=ticker,
                source="alpha_vantage",
                title=None,
                content=result[:1000] if len(result) > 1000 else result,  # Limit size
                url=None,
                published_at=None,
            )
    except Exception:
        pass
    
    return result

def get_global_news(curr_date, look_back_days: int = 7, limit: int = 50) -> dict[str, str] | str:
    """Returns global market news & sentiment data without ticker-specific filtering.

    Covers broad market topics like financial markets, economy, and more.

    Args:
        curr_date: Current date in yyyy-mm-dd format.
        look_back_days: Number of days to look back (default 7).
        limit: Maximum number of articles (default 50).

    Returns:
        Dictionary containing global news sentiment data or JSON string.
    """
    from datetime import datetime, timedelta

    # Calculate start date
    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - timedelta(days=look_back_days)
    start_date = start_dt.strftime("%Y-%m-%d")

    params = {
        "topics": "financial_markets,economy_macro,economy_monetary",
        "time_from": format_datetime_for_api(start_date),
        "time_to": format_datetime_for_api(curr_date),
        "limit": str(limit),
    }

    result = _make_api_request("NEWS_SENTIMENT", params)
    
    # Lineage: record raw news data when DB is enabled
    try:
        from tradingagents.graph.lineage import try_record_raw_news
        # Parse result if it's a dict, extract news items
        if isinstance(result, dict) and "feed" in result:
            for item in result.get("feed", [])[:limit]:
                try_record_raw_news(
                    ticker=None,  # Global news, no specific ticker
                    source="alpha_vantage",
                    title=item.get("title"),
                    content=item.get("summary"),
                    url=item.get("url"),
                    published_at=item.get("time_published"),
                )
        elif isinstance(result, str):
            try_record_raw_news(
                ticker=None,
                source="alpha_vantage",
                title=None,
                content=result[:1000] if len(result) > 1000 else result,
                url=None,
                published_at=None,
            )
    except Exception:
        pass
    
    return result


def get_insider_transactions(symbol: str) -> dict[str, str] | str:
    """Returns latest and historical insider transactions by key stakeholders.

    Covers transactions by founders, executives, board members, etc.

    Args:
        symbol: Ticker symbol. Example: "IBM".

    Returns:
        Dictionary containing insider transaction data or JSON string.
    """

    params = {
        "symbol": symbol,
    }

    result = _make_api_request("INSIDER_TRANSACTIONS", params)
    
    # Lineage: record insider transactions as news data when DB is enabled
    try:
        from tradingagents.graph.lineage import try_record_raw_news
        # Record insider transactions as news-like data
        if isinstance(result, dict):
            transactions = result.get("transactions", [])
            for trans in transactions[:50]:  # Limit to 50 transactions
                try_record_raw_news(
                    ticker=symbol,
                    source="alpha_vantage",
                    title=f"Insider Transaction: {trans.get('transaction_type', 'Unknown')}",
                    content=str(trans),
                    url=None,
                    published_at=trans.get("transaction_date"),
                )
        elif isinstance(result, str):
            try_record_raw_news(
                ticker=symbol,
                source="alpha_vantage",
                title="Insider Transactions",
                content=result[:1000] if len(result) > 1000 else result,
                url=None,
                published_at=None,
            )
    except Exception:
        pass
    
    return result
