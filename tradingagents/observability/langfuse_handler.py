"""Langfuse observability integration for TradingAgents.

Creates a LangChain-compatible callback handler that sends traces
to a Langfuse instance (self-hosted or cloud).

The handler is optional — if Langfuse is not configured, a no-op
fallback is returned so the rest of the system works unchanged.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def create_langfuse_handler(
    config: dict[str, Any] | None = None,
) -> Any | None:
    """Create a Langfuse callback handler for LangChain.

    Configuration is read from ``config`` dict or environment variables:
      - LANGFUSE_PUBLIC_KEY
      - LANGFUSE_SECRET_KEY
      - LANGFUSE_HOST  (defaults to http://localhost:3000)

    Returns:
        A CallbackHandler instance, or None if Langfuse is not available
        or not configured.
    """
    config = config or {}

    public_key = config.get("langfuse_public_key") or os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = config.get("langfuse_secret_key") or os.environ.get("LANGFUSE_SECRET_KEY")
    host = config.get("langfuse_host") or os.environ.get("LANGFUSE_HOST", "http://localhost:3000")

    if not public_key or not secret_key:
        logger.debug(
            "Langfuse keys not configured — observability disabled. "
            "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable."
        )
        return None

    try:
        from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

        handler = LangfuseCallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("Langfuse observability enabled (host=%s)", host)
        return handler

    except ImportError:
        logger.warning(
            "langfuse package not installed — observability disabled. "
            "Install with: pip install langfuse"
        )
        return None
    except Exception as exc:
        logger.warning("Failed to initialize Langfuse handler: %s", exc)
        return None
