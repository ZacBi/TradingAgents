from __future__ import annotations

from fastapi import FastAPI

from tradingagents.api.routers import portfolio, decisions


def create_app() -> FastAPI:
    """Create FastAPI app and register routers."""
    app = FastAPI(
        title="TradingAgents API",
        description="FastAPI backend for TradingAgents single-user dashboard.",
        version="0.1.0",
    )

    app.include_router(portfolio.router, prefix="/api/v1", tags=["portfolio"])
    app.include_router(decisions.router, prefix="/api/v1", tags=["decisions"])

    return app


app = create_app()

