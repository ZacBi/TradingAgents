"""Alembic environment configuration for TradingAgents.

Configures Alembic to:
1. Support both SQLite and PostgreSQL backends
2. Auto-detect model changes via metadata comparison
3. Handle async connections (future-ready)
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add parent directory to path for model imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import Base and all models for metadata
from tradingagents.database.models import (
    AgentDecision,
    Base,
    DailyNav,
    DecisionDataLink,
    Position,
    RawDeepResearch,
    RawFundamentals,
    RawMacroData,
    RawMarketData,
    RawNews,
    RawSocialSentiment,
    Trade,
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata from Base
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from environment or config.

    Priority:
    1. DATABASE_URL environment variable
    2. POSTGRES_URL environment variable
    3. alembic.ini sqlalchemy.url
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    
    url = os.environ.get("POSTGRES_URL")
    if url:
        return url
    
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare type changes for columns
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare type changes for columns
            compare_type=True,
            # Include schemas for postgres
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
