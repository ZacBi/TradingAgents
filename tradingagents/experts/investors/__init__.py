# TradingAgents/experts/investors/__init__.py
"""Investment expert agent implementations."""

from .buffett import BUFFETT_PROFILE, create_buffett_agent
from .graham import GRAHAM_PROFILE, create_graham_agent
from .livermore import LIVERMORE_PROFILE, create_livermore_agent
from .lynch import LYNCH_PROFILE, create_lynch_agent
from .munger import MUNGER_PROFILE, create_munger_agent

__all__ = [
    "BUFFETT_PROFILE",
    "create_buffett_agent",
    "MUNGER_PROFILE",
    "create_munger_agent",
    "LYNCH_PROFILE",
    "create_lynch_agent",
    "LIVERMORE_PROFILE",
    "create_livermore_agent",
    "GRAHAM_PROFILE",
    "create_graham_agent",
]
