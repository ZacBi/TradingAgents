"""FastAPI application for TradingAgents web API.

This module exposes a FastAPI app instance that can be used by ASGI servers
like uvicorn:

    uv run uvicorn tradingagents.api:app --reload

The API is intentionally minimal for now and focuses on read-only endpoints
for portfolio/positions/NAV and decisions. It builds on top of the existing
SQLAlchemy-based DatabaseManager.
"""

from .app import app  # re-export for uvicorn convenience

__all__ = ["app"]

