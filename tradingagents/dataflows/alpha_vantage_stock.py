from datetime import datetime

from .alpha_vantage_common import _filter_csv_by_date_range, _make_api_request


def get_stock(
    symbol: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Returns raw daily OHLCV values, adjusted close values, and historical split/dividend events
    filtered to the specified date range.

    Args:
        symbol: The name of the equity. For example: symbol=IBM
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format

    Returns:
        CSV string containing the daily adjusted time series data filtered to the date range.
    """
    # Parse dates to determine the range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    today = datetime.now()

    # Choose outputsize based on whether the requested range is within the latest 100 days
    # Compact returns latest 100 data points, so check if start_date is recent enough
    days_from_today_to_start = (today - start_dt).days
    outputsize = "compact" if days_from_today_to_start < 100 else "full"

    params = {
        "symbol": symbol,
        "outputsize": outputsize,
        "datatype": "csv",
    }

    response = _make_api_request("TIME_SERIES_DAILY_ADJUSTED", params)
    filtered_response = _filter_csv_by_date_range(response, start_date, end_date)
    
    # Lineage: record raw market data when DB is enabled
    try:
        from tradingagents.graph.lineage import try_record_raw_market_data
        # Convert CSV string to dict for storage (simplified)
        try_record_raw_market_data(
            ticker=symbol,
            trade_date=end_date,
            price_data=filtered_response[:1000] if len(filtered_response) > 1000 else filtered_response,  # Limit size
            indicators=None,
            source="alpha_vantage",
        )
    except Exception:
        pass
    
    return filtered_response
