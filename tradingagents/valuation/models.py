# tradingagents/valuation/models.py
"""价值投资计算引擎 - DCF、Graham Number、WACC 估算。

纯 Python 实现，无外部数学库依赖。
"""

import math
import logging
from typing import Literal
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class FinancialMetrics(TypedDict, total=False):
    """从 fundamentals_report 或 yfinance 提取的结构化财务指标。"""
    current_price: float
    free_cashflow: float
    operating_cashflow: float
    capital_expenditures: float
    shares_outstanding: float
    trailing_eps: float
    forward_eps: float
    book_value: float           # per share
    beta: float
    debt_to_equity: float
    revenue_growth: float
    earnings_growth: float
    profit_margins: float
    return_on_equity: float
    market_cap: float
    enterprise_value: float
    sector: str
    industry: str


class DCFResult(TypedDict):
    """DCF 估值结果。"""
    intrinsic_value: float      # 每股内在价值（基准场景）
    current_price: float
    upside_pct: float           # (intrinsic - price) / price * 100
    wacc: float
    scenarios: dict             # {"bear": float, "base": float, "bull": float}


class GrahamNumberResult(TypedDict):
    """Graham Number 估值结果。"""
    graham_number: float
    current_price: float
    margin_of_safety: float     # (graham - price) / graham
    is_undervalued: bool


class ValuationResult(TypedDict):
    """聚合估值结果。"""
    ticker: str
    analysis_date: str
    dcf: DCFResult | None
    graham: GrahamNumberResult | None
    moat: dict | None           # MoatAssessment from LLM
    recommendation: str         # "Strong Buy" | "Buy" | "Hold" | "Sell"
    confidence: str             # "High" | "Medium" | "Low"
    report: str                 # Markdown 格式报告


# ---------------------------------------------------------------------------
# WACC 估算
# ---------------------------------------------------------------------------

def estimate_wacc(
    metrics: FinancialMetrics,
    risk_free_rate: float = 0.04,
    market_risk_premium: float = 0.06,
) -> float:
    """估算加权平均资本成本 (WACC)。

    WACC = (E/V)*Re + (D/V)*Rd*(1-T)
    Re = Rf + Beta * MRP

    Args:
        metrics: 财务指标
        risk_free_rate: 无风险利率，默认 4%
        market_risk_premium: 市场风险溢价，默认 6%

    Returns:
        WACC 作为小数 (如 0.085 表示 8.5%)
    """
    beta = metrics.get("beta", 1.0)
    if beta is None or beta <= 0:
        beta = 1.0

    # 权益成本
    cost_of_equity = risk_free_rate + beta * market_risk_premium

    # 债务权益比 → 推导债务占比
    debt_to_equity = metrics.get("debt_to_equity", 0.0)
    if debt_to_equity is None or debt_to_equity < 0:
        debt_to_equity = 0.0

    # D/E → E/(D+E) 和 D/(D+E)
    equity_weight = 1.0 / (1.0 + debt_to_equity / 100.0)  # yfinance D/E 通常为百分数值
    debt_weight = 1.0 - equity_weight

    # 债务成本估算（简化：无风险利率 + 信用溢价）
    if debt_to_equity > 200:
        credit_spread = 0.04     # 高杠杆
    elif debt_to_equity > 100:
        credit_spread = 0.025
    elif debt_to_equity > 50:
        credit_spread = 0.015
    else:
        credit_spread = 0.01
    cost_of_debt = risk_free_rate + credit_spread

    # 假设有效税率 21%
    tax_rate = 0.21

    wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - tax_rate)

    # 合理性检查：WACC 限制在 4%-20%
    wacc = max(0.04, min(0.20, wacc))

    logger.debug(
        "WACC=%.4f (Re=%.4f, Rd=%.4f, E/V=%.2f, D/V=%.2f, beta=%.2f)",
        wacc, cost_of_equity, cost_of_debt, equity_weight, debt_weight, beta,
    )
    return wacc


# ---------------------------------------------------------------------------
# DCF 模型
# ---------------------------------------------------------------------------

def calculate_dcf(
    metrics: FinancialMetrics,
    projection_years: int = 5,
    terminal_growth_rate: float = 0.025,
    risk_free_rate: float = 0.04,
    market_risk_premium: float = 0.06,
) -> DCFResult | None:
    """使用自由现金流折现模型计算内在价值。

    Args:
        metrics: 财务指标（需含 free_cashflow, shares_outstanding, current_price）
        projection_years: 预测年数
        terminal_growth_rate: 永续增长率
        risk_free_rate: 无风险利率
        market_risk_premium: 市场风险溢价

    Returns:
        DCFResult 或 None（若数据不足无法计算）
    """
    fcf = metrics.get("free_cashflow")
    shares = metrics.get("shares_outstanding")
    price = metrics.get("current_price")

    # FCF 不可用时尝试 operating_cashflow - capex
    if not fcf or fcf <= 0:
        op_cf = metrics.get("operating_cashflow")
        capex = metrics.get("capital_expenditures")
        if op_cf and capex and op_cf > 0:
            fcf = op_cf - abs(capex)
            logger.info("使用 OCF - CapEx 估算 FCF: %.0f", fcf)

    if not fcf or fcf <= 0:
        logger.warning("FCF <= 0 或不可用，跳过 DCF 计算")
        return None
    if not shares or shares <= 0:
        logger.warning("流通股数不可用，跳过 DCF 计算")
        return None
    if not price or price <= 0:
        logger.warning("当前价格不可用，跳过 DCF 计算")
        return None

    wacc = estimate_wacc(metrics, risk_free_rate, market_risk_premium)

    # 增长率：取 revenue_growth 和 earnings_growth 的平均，若不可用则用 5%
    rev_g = metrics.get("revenue_growth")
    earn_g = metrics.get("earnings_growth")
    growth_rates = [g for g in [rev_g, earn_g] if g is not None and -1 < g < 2]
    base_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0.05

    # 三场景
    scenarios_config = {
        "bear": {"growth_adj": -0.03, "tg_adj": -0.01, "wacc_adj": 0.01},
        "base": {"growth_adj": 0.0, "tg_adj": 0.0, "wacc_adj": 0.0},
        "bull": {"growth_adj": 0.02, "tg_adj": 0.005, "wacc_adj": -0.005},
    }

    scenarios: dict[str, float] = {}
    for scenario, adj in scenarios_config.items():
        g = max(0.0, base_growth + adj["growth_adj"])
        tg = terminal_growth_rate + adj["tg_adj"]
        w = wacc + adj["wacc_adj"]

        # 安全检查：WACC 必须大于终端增长率
        if w <= tg:
            tg = w - 0.02

        iv = _dcf_intrinsic_value(fcf, g, w, tg, projection_years, shares)
        scenarios[scenario] = round(iv, 2)

    base_iv = scenarios["base"]
    upside_pct = (base_iv - price) / price * 100

    return DCFResult(
        intrinsic_value=base_iv,
        current_price=round(price, 2),
        upside_pct=round(upside_pct, 2),
        wacc=round(wacc, 4),
        scenarios=scenarios,
    )


def _dcf_intrinsic_value(
    fcf: float,
    growth_rate: float,
    wacc: float,
    terminal_growth: float,
    years: int,
    shares: float,
) -> float:
    """DCF 核心计算：预测 FCF → 折现 → 每股价值。"""
    # 预测未来各年 FCF 并折现
    pv_fcfs = 0.0
    projected_fcf = fcf
    for t in range(1, years + 1):
        projected_fcf *= (1 + growth_rate)
        pv_fcfs += projected_fcf / ((1 + wacc) ** t)

    # 终值
    terminal_fcf = projected_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** years)

    # 企业价值 → 每股
    enterprise_value = pv_fcfs + pv_terminal
    per_share = enterprise_value / shares
    return max(0.0, per_share)


# ---------------------------------------------------------------------------
# Graham Number
# ---------------------------------------------------------------------------

def calculate_graham_number(
    eps: float,
    book_value_per_share: float,
    current_price: float,
) -> GrahamNumberResult | None:
    """计算 Graham Number。

    Graham Number = sqrt(22.5 * EPS * BVPS)

    Args:
        eps: 每股收益（TTM）
        book_value_per_share: 每股账面价值
        current_price: 当前股价

    Returns:
        GrahamNumberResult 或 None（若 EPS/BVPS <= 0）
    """
    if eps is None or eps <= 0:
        logger.warning("EPS <= 0 (%.2f)，跳过 Graham Number 计算", eps or 0)
        return None
    if book_value_per_share is None or book_value_per_share <= 0:
        logger.warning("BVPS <= 0 (%.2f)，跳过 Graham Number 计算", book_value_per_share or 0)
        return None
    if current_price is None or current_price <= 0:
        logger.warning("当前价格无效，跳过 Graham Number 计算")
        return None

    graham = math.sqrt(22.5 * eps * book_value_per_share)
    margin_of_safety = (graham - current_price) / graham

    return GrahamNumberResult(
        graham_number=round(graham, 2),
        current_price=round(current_price, 2),
        margin_of_safety=round(margin_of_safety, 4),
        is_undervalued=margin_of_safety > 0,
    )
