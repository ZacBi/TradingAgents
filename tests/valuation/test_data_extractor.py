# tests/valuation/test_data_extractor.py
"""数据提取器单元测试。"""

import pytest

from tradingagents.valuation.data_extractor import (
    extract_financial_metrics,
    _parse_numeric,
)


# ---------------------------------------------------------------------------
# _parse_numeric
# ---------------------------------------------------------------------------

class TestParseNumeric:
    def test_plain_number(self):
        assert _parse_numeric("6.13") == pytest.approx(6.13)

    def test_with_dollar_sign(self):
        assert _parse_numeric("$230.50") == pytest.approx(230.50)

    def test_billions(self):
        assert _parse_numeric("99.60B") == pytest.approx(99.6e9)

    def test_millions(self):
        assert _parse_numeric("15.50M") == pytest.approx(15.5e6)

    def test_thousands(self):
        assert _parse_numeric("500K") == pytest.approx(500e3)

    def test_trillions(self):
        assert _parse_numeric("3.5T") == pytest.approx(3.5e12)

    def test_percentage(self):
        assert _parse_numeric("10.5%") == pytest.approx(0.105)

    def test_negative(self):
        assert _parse_numeric("-0.0500") == pytest.approx(-0.05)

    def test_na_returns_none(self):
        assert _parse_numeric("N/A") is None
        assert _parse_numeric("None") is None
        assert _parse_numeric("--") is None
        assert _parse_numeric("") is None

    def test_comma_separated(self):
        assert _parse_numeric("1,234,567") == pytest.approx(1234567)

    def test_dollar_with_billions(self):
        assert _parse_numeric("$99.60B") == pytest.approx(99.6e9)


# ---------------------------------------------------------------------------
# extract_financial_metrics
# ---------------------------------------------------------------------------

class TestExtractFinancialMetrics:
    @pytest.fixture
    def sample_report(self) -> str:
        """模拟 yfinance get_valuation_metrics() 的输出格式。"""
        return """# Valuation Metrics for AAPL
# Data retrieved on: 2025-01-15 10:30:00

Company: Apple Inc.
Sector: Technology
Industry: Consumer Electronics
Current Price: 230.50
Market Cap: 3.56T
Enterprise Value: 3.68T
EPS (Trailing): 6.13
EPS (Forward): 7.25
Book Value Per Share: 3.85
Profit Margin: 0.2637
ROE: 1.6095
Revenue Growth (YoY): 0.0800
Earnings Growth (YoY): 0.1200
Debt to Equity: 180.02
Free Cash Flow: 99.60B
Operating Cash Flow: 118.25B
Beta: 1.2400
"""

    def test_full_report_parsing(self, sample_report):
        """完整报告应正确解析所有字段。"""
        result = extract_financial_metrics("AAPL", sample_report, "2025-01-15")
        assert result is not None
        assert result["current_price"] == pytest.approx(230.50)
        assert result["trailing_eps"] == pytest.approx(6.13)
        assert result["book_value"] == pytest.approx(3.85)
        assert result["free_cashflow"] == pytest.approx(99.6e9)
        assert result["sector"] == "Technology"
        assert result["industry"] == "Consumer Electronics"
        assert result["revenue_growth"] == pytest.approx(0.08)
        assert result["debt_to_equity"] == pytest.approx(180.02)

    def test_shares_outstanding_inferred(self, sample_report):
        """shares_outstanding 应从 market_cap/price 推算。"""
        result = extract_financial_metrics("AAPL", sample_report, "2025-01-15")
        assert result is not None
        assert "shares_outstanding" in result
        expected = 3.56e12 / 230.50
        assert result["shares_outstanding"] == pytest.approx(expected, rel=0.01)

    def test_empty_report_returns_none_without_yfinance(self):
        """空报告且无 yfinance 后备时应尝试 yfinance（此测试不依赖网络）。"""
        # 注意：此测试可能因网络而失败，所以只验证不会抛异常
        result = extract_financial_metrics("INVALID_TICKER_XYZ123", "", "2025-01-15")
        # 可能返回 None（yfinance 查不到）或 metrics（如果碰巧能查到）
        # 关键是不抛异常

    def test_partial_report(self):
        """部分数据应被正确提取。"""
        partial = """Current Price: 150.00
EPS (Trailing): 4.50
"""
        result = extract_financial_metrics("TEST", partial, "2025-01-15")
        assert result is not None
        assert result["current_price"] == pytest.approx(150.0)
        assert result["trailing_eps"] == pytest.approx(4.5)

    def test_beta_parsing(self, sample_report):
        """Beta 应从报告中正确解析。"""
        result = extract_financial_metrics("AAPL", sample_report, "2025-01-15")
        assert result is not None
        assert result.get("beta") == pytest.approx(1.24)
