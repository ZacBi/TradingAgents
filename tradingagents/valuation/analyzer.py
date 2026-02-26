# tradingagents/valuation/analyzer.py
"""估值分析主编排器。

串联 data_extractor + models (DCF/Graham) + moat_analyzer (LLM)，
产出综合估值报告并写入 AgentState.valuation_result。
"""

import json
import logging
from collections.abc import Callable
from datetime import datetime

from .data_extractor import extract_financial_metrics
from .moat_analyzer import create_moat_analyzer
from .models import (
    DCFResult,
    GrahamNumberResult,
    ValuationResult,
    calculate_dcf,
    calculate_graham_number,
)

logger = logging.getLogger(__name__)


def create_valuation_node(
    llm,
    prompt_manager: object | None = None,
    config: dict | None = None,
) -> Callable:
    """创建 Valuation Analyst 节点。

    该节点作为 LangGraph 工作流中的一个 node，接收 AgentState 并返回
    包含 valuation_result 的状态更新。

    Args:
        llm: LangChain LLM 实例（用于 moat 分析）
        prompt_manager: PromptManager 实例
        config: 全局配置字典

    Returns:
        valuation_node(state: AgentState) -> dict
    """
    config = config or {}
    moat_node = create_moat_analyzer(llm, prompt_manager)

    def valuation_node(state: dict) -> dict:
        """执行完整估值分析流水线。"""
        ticker = state.get("company_of_interest", "UNKNOWN")
        trade_date = state.get("trade_date", "")
        fundamentals_report = state.get("fundamentals_report", "")

        logger.info("开始估值分析: %s @ %s", ticker, trade_date)

        # Step 1: 提取财务指标
        metrics = extract_financial_metrics(ticker, fundamentals_report, trade_date)

        # Step 2: DCF 计算
        dcf_result = None
        if metrics:
            dcf_result = calculate_dcf(
                metrics,
                projection_years=config.get("valuation_dcf_projection_years", 5),
                terminal_growth_rate=config.get("valuation_terminal_growth_rate", 0.025),
                risk_free_rate=config.get("valuation_risk_free_rate", 0.04),
                market_risk_premium=config.get("valuation_market_risk_premium", 0.06),
            )

        # Step 3: Graham Number 计算
        graham_result = None
        if metrics:
            eps = metrics.get("trailing_eps")
            bvps = metrics.get("book_value")
            price = metrics.get("current_price")
            if eps and bvps and price:
                graham_result = calculate_graham_number(eps, bvps, price)

        # Step 4: Moat 评估 (LLM)
        moat_result = None
        try:
            moat_state = moat_node(state)
            moat_result = moat_state.get("_moat_assessment")
        except Exception as exc:
            logger.warning("Moat 分析异常: %s", exc)

        # Step 5: 综合决策
        recommendation, confidence = _synthesize_recommendation(
            dcf_result, graham_result, moat_result
        )

        # Step 6: 生成报告
        report = _format_report(
            ticker, trade_date, dcf_result, graham_result, moat_result,
            recommendation, confidence,
        )

        # 组装结果
        result = ValuationResult(
            ticker=ticker,
            analysis_date=trade_date or datetime.now().strftime("%Y-%m-%d"),
            dcf=dcf_result,
            graham=graham_result,
            moat=moat_result,
            recommendation=recommendation,
            confidence=confidence,
            report=report,
        )

        logger.info(
            "估值分析完成: %s → %s (confidence=%s)",
            ticker, recommendation, confidence,
        )

        return {"valuation_result": json.dumps(result, ensure_ascii=False)}

    return valuation_node


def _dcf_upside_score(dcf_upside: float) -> int:
    """DCF upside 百分制评分."""
    if dcf_upside > 50:
        return 90
    if dcf_upside > 30:
        return 75
    if dcf_upside > 10:
        return 55
    if dcf_upside > 0:
        return 40
    return 20


def _graham_mos_score(graham_mos: float) -> int:
    """Graham margin of safety 百分制评分."""
    if graham_mos > 0.30:
        return 90
    if graham_mos > 0.10:
        return 70
    if graham_mos > 0:
        return 50
    return 25


def _moat_bonus(moat: dict | None) -> int:
    """Moat 评级加权分."""
    if not moat:
        return 0
    rating = moat.get("moat_rating", "None")
    if rating == "Wide":
        return 15
    if rating == "Narrow":
        return 5
    return 0


def _score_to_recommendation(avg_score: float) -> str:
    """平均分映射到买卖建议."""
    if avg_score >= 80:
        return "Strong Buy"
    if avg_score >= 60:
        return "Buy"
    if avg_score >= 40:
        return "Hold"
    return "Sell"


def _synthesize_confidence(
    available: int, moat: dict | None, scores: list[int]
) -> str:
    """根据数据完整性与信号一致性得到置信度."""
    if available >= 2 and moat is not None and scores and (max(scores) - min(scores) < 30):
        return "High"
    if available >= 1:
        return "Medium"
    return "Low"


def _synthesize_recommendation(
    dcf: DCFResult | None,
    graham: GrahamNumberResult | None,
    moat: dict | None,
) -> tuple[str, str]:
    """根据三项估值指标综合决策。

    Returns:
        (recommendation, confidence) 元组
    """
    dcf_upside = dcf["upside_pct"] if dcf else None
    graham_mos = graham["margin_of_safety"] if graham else None
    moat_rating = moat.get("moat_rating", "None") if moat else "None"
    available = sum(1 for x in [dcf_upside, graham_mos] if x is not None)
    has_moat = moat is not None and moat_rating != "None"

    if available == 0 and not has_moat:
        return "Hold", "Low"

    scores = []
    if dcf_upside is not None:
        scores.append(_dcf_upside_score(dcf_upside))
    if graham_mos is not None:
        scores.append(_graham_mos_score(graham_mos))

    bonus = _moat_bonus(moat)
    avg_score = (sum(scores) / len(scores) + bonus) if scores else (40 + bonus)
    recommendation = _score_to_recommendation(avg_score)
    confidence = _synthesize_confidence(available, moat, scores)
    return recommendation, confidence


def _format_report(
    ticker: str,
    trade_date: str,
    dcf: DCFResult | None,
    graham: GrahamNumberResult | None,
    moat: dict | None,
    recommendation: str,
    confidence: str,
) -> str:
    """生成 Markdown 格式的估值报告。"""
    lines = [f"## Valuation Analysis - {ticker}"]
    if trade_date:
        lines.append(f"*Analysis Date: {trade_date}*\n")

    # DCF 部分
    lines.append("### DCF Model")
    if dcf:
        lines.append(f"- Intrinsic Value (Base): ${dcf['intrinsic_value']:.2f}")
        lines.append(f"- Current Price: ${dcf['current_price']:.2f}")
        lines.append(f"- Upside: {dcf['upside_pct']:.1f}%")
        lines.append(f"- WACC: {dcf['wacc']:.2%}")
        sc = dcf["scenarios"]
        lines.append(f"- Scenarios: Bear ${sc.get('bear', 0):.2f} | Base ${sc.get('base', 0):.2f} | Bull ${sc.get('bull', 0):.2f}")
    else:
        lines.append("- *DCF calculation not available (insufficient data)*")
    lines.append("")

    # Graham 部分
    lines.append("### Graham Number")
    if graham:
        lines.append(f"- Graham Number: ${graham['graham_number']:.2f}")
        lines.append(f"- Current Price: ${graham['current_price']:.2f}")
        lines.append(f"- Margin of Safety: {graham['margin_of_safety']:.1%}")
        status = "Undervalued" if graham["is_undervalued"] else "Overvalued"
        lines.append(f"- Status: {status}")
    else:
        lines.append("- *Graham Number not available (requires positive EPS and BVPS)*")
    lines.append("")

    # Moat 部分
    lines.append("### Economic Moat")
    if moat:
        lines.append(f"- Rating: {moat.get('moat_rating', 'N/A')}")
        sources = moat.get("moat_sources", [])
        if sources:
            lines.append(f"- Sources: {', '.join(sources)}")
        lines.append(f"- Sustainability: {moat.get('sustainability_score', 'N/A')}/10")
        reasoning = moat.get("reasoning", "")
        if reasoning:
            lines.append(f"- Analysis: {reasoning}")
    else:
        lines.append("- *Moat assessment not available*")
    lines.append("")

    # 综合建议
    lines.append("### Overall Recommendation")
    lines.append(f"**{recommendation}** (Confidence: {confidence})")
    lines.append("")
    lines.append("*This valuation is for reference only and does not constitute investment advice.*")

    return "\n".join(lines)
