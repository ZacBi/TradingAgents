# tradingagents/valuation/data_extractor.py
"""从 fundamentals_report 或 yfinance 提取结构化财务指标。"""

import re
import logging
from typing import Optional

from .models import FinancialMetrics

logger = logging.getLogger(__name__)

# yfinance_enhanced get_valuation_metrics() 输出格式的字段映射
# 格式: "Label: value" 或 "Label: 99.60B"
_FIELD_MAP = {
    "Current Price": "current_price",
    "Free Cash Flow": "free_cashflow",
    "Operating Cash Flow": "operating_cashflow",
    "EPS (Trailing)": "trailing_eps",
    "EPS (Forward)": "forward_eps",
    "Book Value Per Share": "book_value",
    "Market Cap": "market_cap",
    "Enterprise Value": "enterprise_value",
    "Revenue Growth (YoY)": "revenue_growth",
    "Earnings Growth (YoY)": "earnings_growth",
    "Profit Margin": "profit_margins",
    "ROE": "return_on_equity",
    "Debt to Equity": "debt_to_equity",
    "Sector": "sector",
    "Industry": "industry",
}

# yfinance info 字典键映射（用于直接调用 yfinance 时）
_INFO_KEY_MAP = {
    "currentPrice": "current_price",
    "freeCashflow": "free_cashflow",
    "operatingCashflow": "operating_cashflow",
    "trailingEps": "trailing_eps",
    "forwardEps": "forward_eps",
    "bookValue": "book_value",
    "marketCap": "market_cap",
    "enterpriseValue": "enterprise_value",
    "revenueGrowth": "revenue_growth",
    "earningsGrowth": "earnings_growth",
    "profitMargins": "profit_margins",
    "returnOnEquity": "return_on_equity",
    "debtToEquity": "debt_to_equity",
    "sector": "sector",
    "industry": "industry",
    "beta": "beta",
    "sharesOutstanding": "shares_outstanding",
}


def extract_financial_metrics(
    ticker: str,
    fundamentals_report: str,
    trade_date: str = "",
) -> FinancialMetrics | None:
    """从分析师报告文本中提取结构化财务指标。

    解析策略:
    1. 在 fundamentals_report 中匹配 "Label: value" 格式的键值对
    2. 处理 B/M/K 单位和百分号
    3. 若关键字段缺失，尝试直接调用 yfinance 补充

    Args:
        ticker: 股票代码
        fundamentals_report: 基本面分析师生成的报告文本
        trade_date: 交易日期（用于日志）

    Returns:
        FinancialMetrics 或 None（若数据完全不可用）
    """
    if not fundamentals_report or fundamentals_report.strip() == "":
        logger.warning("fundamentals_report 为空，尝试直接调用 yfinance")
        return _fetch_from_yfinance(ticker)

    metrics: FinancialMetrics = {}

    # 从报告文本中解析
    _parse_report_text(fundamentals_report, metrics)

    # 检查关键字段
    has_price = metrics.get("current_price") is not None
    has_fcf = metrics.get("free_cashflow") is not None
    has_eps = metrics.get("trailing_eps") is not None
    has_bvps = metrics.get("book_value") is not None

    # 若关键字段缺失，尝试 yfinance 补充
    if not (has_price and (has_fcf or has_eps)):
        logger.info("报告中关键字段缺失，尝试 yfinance 补充 (ticker=%s)", ticker)
        yf_metrics = _fetch_from_yfinance(ticker)
        if yf_metrics:
            _merge_metrics(metrics, yf_metrics)

    # 最终检查：至少需要价格
    if not metrics.get("current_price"):
        logger.warning("无法获取 %s 的当前价格，返回 None", ticker)
        return None

    return metrics


def _parse_report_text(text: str, metrics: FinancialMetrics) -> None:
    """从报告文本中解析键值对到 metrics 字典。"""
    for label, field_name in _FIELD_MAP.items():
        # 匹配 "Label: value" 格式
        pattern = re.escape(label) + r":\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue

        raw_value = match.group(1).strip()
        if field_name in ("sector", "industry"):
            metrics[field_name] = raw_value
        else:
            parsed = _parse_numeric(raw_value)
            if parsed is not None:
                metrics[field_name] = parsed

    # 尝试额外解析 yfinance info 风格的键值对 (如 "beta: 1.25")
    _parse_info_style_keys(text, metrics)

    # 推算 shares_outstanding
    if "shares_outstanding" not in metrics:
        mc = metrics.get("market_cap")
        price = metrics.get("current_price")
        if mc and price and price > 0:
            metrics["shares_outstanding"] = mc / price


def _parse_info_style_keys(text: str, metrics: FinancialMetrics) -> None:
    """解析 yfinance info 风格的键值对（如 beta: 1.25, sharesOutstanding: 15.5B）。"""
    extra_patterns = {
        "beta": "beta",
        "sharesOutstanding": "shares_outstanding",
        "Shares Outstanding": "shares_outstanding",
        "Beta": "beta",
    }
    for label, field_name in extra_patterns.items():
        if field_name in metrics:
            continue
        pattern = re.escape(label) + r":\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = _parse_numeric(match.group(1).strip())
            if parsed is not None:
                metrics[field_name] = parsed


def _parse_numeric(raw: str) -> float | None:
    """解析带单位的数值字符串。

    支持格式: "$99.6B", "99.60B", "10.5%", "6.13", "-0.0500", "N/A"
    """
    if not raw or raw.lower() in ("n/a", "none", "null", "--", ""):
        return None

    # 去除 $ 和逗号
    cleaned = raw.replace("$", "").replace(",", "").strip()

    # 百分号处理（保留为小数形式）
    if cleaned.endswith("%"):
        try:
            return float(cleaned[:-1]) / 100.0
        except ValueError:
            return None

    # 单位乘数
    multiplier = 1.0
    if cleaned.upper().endswith("T"):
        multiplier = 1e12
        cleaned = cleaned[:-1]
    elif cleaned.upper().endswith("B"):
        multiplier = 1e9
        cleaned = cleaned[:-1]
    elif cleaned.upper().endswith("M"):
        multiplier = 1e6
        cleaned = cleaned[:-1]
    elif cleaned.upper().endswith("K"):
        multiplier = 1e3
        cleaned = cleaned[:-1]

    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def _fetch_from_yfinance(ticker: str) -> FinancialMetrics | None:
    """直接调用 yfinance 获取财务指标作为后备。"""
    try:
        import yfinance as yf
        ticker_obj = yf.Ticker(ticker.upper())
        info = ticker_obj.info
        if not info:
            return None

        metrics: FinancialMetrics = {}
        for yf_key, field_name in _INFO_KEY_MAP.items():
            val = info.get(yf_key)
            if val is not None:
                metrics[field_name] = val

        # shares_outstanding
        shares = info.get("sharesOutstanding")
        if shares:
            metrics["shares_outstanding"] = float(shares)

        # beta
        beta = info.get("beta")
        if beta:
            metrics["beta"] = float(beta)

        return metrics if metrics else None
    except Exception as exc:
        logger.warning("yfinance 后备查询失败 (%s): %s", ticker, exc)
        return None


def _merge_metrics(target: FinancialMetrics, source: FinancialMetrics) -> None:
    """将 source 中缺失的字段补充到 target。"""
    for key, val in source.items():
        if key not in target or target[key] is None:
            target[key] = val
