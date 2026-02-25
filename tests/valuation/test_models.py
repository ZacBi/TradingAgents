# tests/valuation/test_models.py
"""DCF、Graham Number、WACC 计算引擎单元测试。"""

import math
import pytest

from tradingagents.valuation.models import (
    FinancialMetrics,
    estimate_wacc,
    calculate_dcf,
    calculate_graham_number,
)


# ---------------------------------------------------------------------------
# estimate_wacc
# ---------------------------------------------------------------------------

class TestEstimateWACC:
    def test_default_beta(self):
        """beta=1.0 的标准场景。"""
        metrics: FinancialMetrics = {"beta": 1.0, "debt_to_equity": 0.0}
        wacc = estimate_wacc(metrics, risk_free_rate=0.04, market_risk_premium=0.06)
        # 全权益: Re = 0.04 + 1.0*0.06 = 0.10
        assert abs(wacc - 0.10) < 0.005

    def test_with_leverage(self):
        """有杠杆时 WACC 应低于纯权益成本。"""
        metrics: FinancialMetrics = {"beta": 1.0, "debt_to_equity": 100.0}
        wacc = estimate_wacc(metrics, risk_free_rate=0.04, market_risk_premium=0.06)
        # 有债务 → WACC 应 < Re (因 Rd*(1-T) < Re)
        assert wacc < 0.10
        assert wacc > 0.04  # 不会低于无风险利率

    def test_missing_beta_defaults_to_one(self):
        """缺失 beta 时默认 1.0。"""
        metrics: FinancialMetrics = {}
        wacc = estimate_wacc(metrics)
        assert 0.04 <= wacc <= 0.20

    def test_negative_beta_defaults_to_one(self):
        """负 beta 时默认 1.0。"""
        metrics: FinancialMetrics = {"beta": -0.5}
        wacc = estimate_wacc(metrics)
        assert 0.04 <= wacc <= 0.20

    def test_wacc_clamped(self):
        """WACC 被限制在 4%-20%。"""
        # 极高 beta
        metrics: FinancialMetrics = {"beta": 10.0, "debt_to_equity": 0.0}
        wacc = estimate_wacc(metrics)
        assert wacc <= 0.20


# ---------------------------------------------------------------------------
# calculate_dcf
# ---------------------------------------------------------------------------

class TestCalculateDCF:
    @pytest.fixture
    def apple_like_metrics(self) -> FinancialMetrics:
        """类 Apple 的财务指标。"""
        return FinancialMetrics(
            current_price=230.0,
            free_cashflow=100_000_000_000,  # 100B
            shares_outstanding=15_500_000_000,  # 15.5B
            beta=1.2,
            debt_to_equity=180.0,
            revenue_growth=0.08,
            earnings_growth=0.12,
        )

    def test_positive_fcf_returns_result(self, apple_like_metrics):
        result = calculate_dcf(apple_like_metrics)
        assert result is not None
        assert result["intrinsic_value"] > 0
        assert result["current_price"] == 230.0
        assert "bear" in result["scenarios"]
        assert "base" in result["scenarios"]
        assert "bull" in result["scenarios"]
        # Bull > Base > Bear
        assert result["scenarios"]["bull"] >= result["scenarios"]["base"]
        assert result["scenarios"]["base"] >= result["scenarios"]["bear"]

    def test_negative_fcf_returns_none(self):
        metrics: FinancialMetrics = {
            "current_price": 100.0,
            "free_cashflow": -50_000_000_000,
            "shares_outstanding": 1_000_000_000,
        }
        result = calculate_dcf(metrics)
        assert result is None

    def test_zero_fcf_returns_none(self):
        metrics: FinancialMetrics = {
            "current_price": 100.0,
            "free_cashflow": 0,
            "shares_outstanding": 1_000_000_000,
        }
        result = calculate_dcf(metrics)
        assert result is None

    def test_missing_shares_returns_none(self):
        metrics: FinancialMetrics = {
            "current_price": 100.0,
            "free_cashflow": 50_000_000_000,
        }
        result = calculate_dcf(metrics)
        assert result is None

    def test_missing_price_returns_none(self):
        metrics: FinancialMetrics = {
            "free_cashflow": 50_000_000_000,
            "shares_outstanding": 1_000_000_000,
        }
        result = calculate_dcf(metrics)
        assert result is None

    def test_ocf_minus_capex_fallback(self):
        """FCF 不可用但 OCF/CapEx 可用时应用后备逻辑。"""
        metrics: FinancialMetrics = {
            "current_price": 100.0,
            "operating_cashflow": 80_000_000_000,
            "capital_expenditures": 20_000_000_000,
            "shares_outstanding": 1_000_000_000,
            "beta": 1.0,
        }
        result = calculate_dcf(metrics)
        assert result is not None
        assert result["intrinsic_value"] > 0

    def test_upside_calculation(self, apple_like_metrics):
        result = calculate_dcf(apple_like_metrics)
        assert result is not None
        expected_upside = (result["intrinsic_value"] - 230.0) / 230.0 * 100
        assert abs(result["upside_pct"] - expected_upside) < 0.1


# ---------------------------------------------------------------------------
# calculate_graham_number
# ---------------------------------------------------------------------------

class TestGrahamNumber:
    def test_standard_case(self):
        """EPS=6.13, BVPS=3.85 → Graham ≈ sqrt(22.5*6.13*3.85)。"""
        result = calculate_graham_number(eps=6.13, book_value_per_share=3.85, current_price=230.0)
        assert result is not None
        expected = math.sqrt(22.5 * 6.13 * 3.85)
        assert abs(result["graham_number"] - round(expected, 2)) < 0.02
        # 对于 230 的价格，Graham ~23 → 应该是 overvalued
        assert result["is_undervalued"] is False
        assert result["margin_of_safety"] < 0

    def test_undervalued_stock(self):
        """价格低于 Graham Number 时。"""
        result = calculate_graham_number(eps=10.0, book_value_per_share=50.0, current_price=30.0)
        assert result is not None
        # Graham = sqrt(22.5 * 10 * 50) = sqrt(11250) ≈ 106.07
        assert result["graham_number"] > 100
        assert result["is_undervalued"] is True
        assert result["margin_of_safety"] > 0

    def test_negative_eps_returns_none(self):
        result = calculate_graham_number(eps=-2.0, book_value_per_share=10.0, current_price=50.0)
        assert result is None

    def test_zero_eps_returns_none(self):
        result = calculate_graham_number(eps=0.0, book_value_per_share=10.0, current_price=50.0)
        assert result is None

    def test_negative_bvps_returns_none(self):
        result = calculate_graham_number(eps=5.0, book_value_per_share=-3.0, current_price=50.0)
        assert result is None

    def test_zero_price_returns_none(self):
        result = calculate_graham_number(eps=5.0, book_value_per_share=10.0, current_price=0.0)
        assert result is None

    def test_margin_of_safety_calculation(self):
        """验证安全边际计算。"""
        result = calculate_graham_number(eps=10.0, book_value_per_share=50.0, current_price=80.0)
        assert result is not None
        expected_mos = (result["graham_number"] - 80.0) / result["graham_number"]
        assert abs(result["margin_of_safety"] - round(expected_mos, 4)) < 0.001
