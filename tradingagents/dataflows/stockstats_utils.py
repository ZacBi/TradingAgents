"""Technical indicators calculation using pandas-ta.

Replaces stockstats with pandas-ta for explicit, performant indicator calculation.
"""

import logging
import os
from typing import Annotated

import pandas as pd
import pandas_ta as ta
import yfinance as yf

from tradingagents.config import get_config

logger = logging.getLogger(__name__)


# Mapping from legacy stockstats indicator names to pandas-ta functions
INDICATOR_MAPPING = {
    # Moving Averages
    "close_50_sma": ("sma", {"length": 50}),
    "close_200_sma": ("sma", {"length": 200}),
    "close_10_ema": ("ema", {"length": 10}),
    # MACD - returns DataFrame with multiple columns
    "macd": ("macd", {}),  # Returns MACD_12_26_9
    "macds": ("macd", {}),  # Returns MACDs_12_26_9
    "macdh": ("macd", {}),  # Returns MACDh_12_26_9
    # Momentum
    "rsi": ("rsi", {"length": 14}),
    # Bollinger Bands - returns DataFrame with multiple columns
    "boll": ("bbands", {}),  # Returns BBM_5_2.0
    "boll_ub": ("bbands", {}),  # Returns BBU_5_2.0
    "boll_lb": ("bbands", {}),  # Returns BBL_5_2.0
    # Volatility
    "atr": ("atr", {"length": 14}),
    # Volume-based
    "vwma": ("vwma", {"length": 20}),
    "mfi": ("mfi", {"length": 14}),
}


def _get_ohlcv(df: pd.DataFrame) -> tuple:
    """Return (close, high, low, volume) with normalized column names."""
    close = df["Close"] if "Close" in df.columns else df["close"]
    high = df["High"] if "High" in df.columns else df.get("high")
    low = df["Low"] if "Low" in df.columns else df.get("low")
    volume = df["Volume"] if "Volume" in df.columns else df.get("volume")
    return close, high, low, volume


def _calc_macd_or_bbands(ta_func, close: pd.Series, indicator: str, func_name: str, kwargs: dict, null_series: pd.Series):
    """Compute MACD or BBANDS and return the requested column."""
    df_out = ta_func(close, **kwargs)
    if df_out is None:
        return null_series
    if func_name == "macd":
        col = {"macd": 0, "macds": 2, "macdh": 1}.get(indicator, 0)
    else:
        col = {"boll": 1, "boll_ub": 2, "boll_lb": 0}.get(indicator, 1)
    return df_out.iloc[:, col]


def _calc_hlv_indicator(
    ta_func, func_name: str, close, high, low, volume, kwargs: dict
) -> pd.Series:
    """Compute ATR, VWMA, or MFI with column checks."""
    if func_name == "atr":
        if high is None or low is None:
            raise ValueError("ATR requires High, Low, Close columns")
        return ta_func(high, low, close, **kwargs)
    if func_name == "vwma":
        if volume is None:
            raise ValueError("VWMA requires Volume column")
        return ta_func(close, volume, **kwargs)
    if high is None or low is None or volume is None:
        raise ValueError("MFI requires High, Low, Close, Volume columns")
    return ta_func(high, low, close, volume, **kwargs)


def calculate_indicator(df: pd.DataFrame, indicator: str) -> pd.Series:
    """Calculate a single indicator using pandas-ta.

    Args:
        df: DataFrame with OHLCV data (Open, High, Low, Close, Volume columns).
        indicator: Indicator name (stockstats-compatible).

    Returns:
        Series with calculated indicator values.
    """
    if indicator not in INDICATOR_MAPPING:
        raise ValueError(
            f"Indicator '{indicator}' not supported. "
            f"Available: {list(INDICATOR_MAPPING.keys())}"
        )
    func_name, kwargs = INDICATOR_MAPPING[indicator]
    ta_func = getattr(ta, func_name, None)
    if ta_func is None:
        raise ValueError(f"pandas-ta function '{func_name}' not found")

    close, high, low, volume = _get_ohlcv(df)
    null_series = pd.Series([None] * len(df), index=df.index)

    if func_name in ("sma", "ema", "rsi"):
        return ta_func(close, **kwargs)
    if func_name in ("macd", "bbands"):
        return _calc_macd_or_bbands(ta_func, close, indicator, func_name, kwargs, null_series)
    if func_name in ("atr", "vwma", "mfi"):
        return _calc_hlv_indicator(ta_func, func_name, close, high, low, volume, kwargs)
    return ta_func(close, **kwargs)


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all supported indicators at once.

    Args:
        df: DataFrame with OHLCV data.

    Returns:
        DataFrame with all indicator columns added.
    """
    result_df = df.copy()

    for indicator in INDICATOR_MAPPING:
        try:
            result_df[indicator] = calculate_indicator(df, indicator)
        except Exception as e:
            logger.warning("Failed to calculate %s: %s", indicator, e)
            result_df[indicator] = None

    return result_df


class StockstatsUtils:
    """Backward-compatible interface for technical indicator calculation."""

    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
    ) -> str:
        """Get a technical indicator value for a specific date.

        Args:
            symbol: Stock ticker symbol.
            indicator: Indicator name (e.g., 'rsi', 'macd', 'close_50_sma').
            curr_date: Date string in YYYY-mm-dd format.

        Returns:
            String representation of the indicator value or error message.
        """
        config = get_config()

        today_date = pd.Timestamp.today()
        curr_date_dt = pd.to_datetime(curr_date)

        end_date = today_date
        start_date = today_date - pd.DateOffset(years=15)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # Ensure cache directory exists
        os.makedirs(config["data_cache_dir"], exist_ok=True)

        data_file = os.path.join(
            config["data_cache_dir"],
            f"{symbol}-YFin-data-{start_date_str}-{end_date_str}.csv",
        )

        # Load or fetch data
        if os.path.exists(data_file):
            data = pd.read_csv(data_file)
            data["Date"] = pd.to_datetime(data["Date"])
        else:
            data = yf.download(
                symbol,
                start=start_date_str,
                end=end_date_str,
                multi_level_index=False,
                progress=False,
                auto_adjust=True,
            )
            data = data.reset_index()
            data.to_csv(data_file, index=False)

        # Calculate indicator using pandas-ta
        try:
            data[indicator] = calculate_indicator(data, indicator)
        except ValueError as e:
            return f"Error: {e}"

        # Format date column for matching
        data["Date"] = data["Date"].dt.strftime("%Y-%m-%d")
        curr_date_str = curr_date_dt.strftime("%Y-%m-%d")

        # Find matching row
        matching_rows = data[data["Date"].str.startswith(curr_date_str)]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            if pd.isna(indicator_value):
                return "N/A: Insufficient data for calculation"
            return str(indicator_value)
        else:
            return "N/A: Not a trading day (weekend or holiday)"
