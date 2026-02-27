from __future__ import annotations

import os
from functools import lru_cache

from tradingagents.config import DEFAULT_CONFIG
from tradingagents.database import DatabaseManager


@lru_cache(maxsize=1)
def get_db_manager() -> DatabaseManager:
    """Return a singleton DatabaseManager based on config/env.

    Preference order:
    1. TRADINGAGENTS_DB_PATH env var (already used by Streamlit dashboard)
    2. DEFAULT_CONFIG["database_path"]
    """
    db_path = os.getenv("TRADINGAGENTS_DB_PATH") or DEFAULT_CONFIG.get(
        "database_path", "tradingagents.db"
    )
    return DatabaseManager(db_path=db_path)

