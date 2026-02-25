# tradingagents/valuation/__init__.py
"""价值投资框架 - Phase 4。

提供 DCF 估值、Graham Number 计算和 LLM 驱动的护城河评估。
"""

from .analyzer import create_valuation_node
from .models import (
    DCFResult,
    FinancialMetrics,
    GrahamNumberResult,
    ValuationResult,
    calculate_dcf,
    calculate_graham_number,
    estimate_wacc,
)

__all__ = [
    "FinancialMetrics",
    "DCFResult",
    "GrahamNumberResult",
    "ValuationResult",
    "estimate_wacc",
    "calculate_dcf",
    "calculate_graham_number",
    "create_valuation_node",
]
