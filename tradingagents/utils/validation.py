"""Shared input validation for graph and CLI entry points."""

import re
from datetime import datetime

# Ticker: non-empty, alphanumeric and dot, max length (e.g. BRK.B)
TICKER_PATTERN = re.compile(r"^[A-Za-z0-9.]{1,12}$")
DATE_FMT = "%Y-%m-%d"


def validate_ticker(value: str) -> None:
    """Validate ticker symbol. Raises ValueError if invalid."""
    if not value or not value.strip():
        raise ValueError("Ticker must be non-empty.")
    s = value.strip()
    if not TICKER_PATTERN.match(s):
        raise ValueError(
            "Ticker must be 1–12 alphanumeric characters or dots (e.g. AAPL, BRK.B)."
        )


def validate_trade_date(
    value: str,
    *,
    allow_future: bool = False,
) -> None:
    """Validate trade date as YYYY-MM-DD. Raises ValueError if invalid."""
    if not value or not value.strip():
        raise ValueError("Trade date must be non-empty.")
    s = value.strip()
    try:
        dt = datetime.strptime(s, DATE_FMT)
    except ValueError:
        raise ValueError("Trade date must be YYYY-MM-DD.") from None
    if not allow_future and dt.date() > datetime.now().date():
        raise ValueError("Trade date must not be in the future.")


def validate_date_range(start_date: str, end_date: str) -> None:
    """Validate start/end dates and start <= end. Raises ValueError if invalid."""
    validate_trade_date(start_date, allow_future=True)
    validate_trade_date(end_date, allow_future=True)
    try:
        start = datetime.strptime(start_date.strip(), DATE_FMT).date()
        end = datetime.strptime(end_date.strip(), DATE_FMT).date()
    except ValueError:
        raise ValueError("Start and end must be YYYY-MM-DD.") from None
    if start > end:
        raise ValueError("Start date must be <= end date.")


def parse_date(s: str) -> datetime | None:
    """Parse YYYY-MM-DD string to datetime; return None if invalid."""
    try:
        return datetime.strptime(s.strip(), DATE_FMT)
    except (ValueError, AttributeError):
        return None
