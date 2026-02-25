# tradingagents/valuation/moat_analyzer.py
"""LLM 驱动的经济护城河评估 Agent。

复用 Expert Agent 模式（参考 buffett.py），通过 PromptManager
获取 prompt 模板，调用 LLM 进行定性护城河分析。
"""

import json
import logging
from typing import Callable, Optional

from tradingagents.prompts import PromptNames, get_prompt_manager

logger = logging.getLogger(__name__)

# Moat 评估的 JSON Schema，用于指导 LLM 输出格式
MOAT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "moat_rating": {
            "type": "string",
            "enum": ["Wide", "Narrow", "None"],
            "description": "Economic moat width assessment",
        },
        "moat_sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Sources of competitive advantage (e.g., brand, network_effect, cost_advantage, switching_costs, intangible_assets)",
        },
        "sustainability_score": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "How sustainable is the moat (1=very fragile, 10=extremely durable)",
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of moat assessment rationale",
        },
    },
    "required": ["moat_rating", "moat_sources", "sustainability_score", "reasoning"],
}

# 默认回退值（LLM 调用失败时使用）
_DEFAULT_MOAT = {
    "moat_rating": "None",
    "moat_sources": [],
    "sustainability_score": 5,
    "reasoning": "Unable to assess moat due to LLM analysis failure.",
}


def create_moat_analyzer(llm, prompt_manager: Optional[object] = None) -> Callable:
    """创建护城河评估 Agent 节点。

    Args:
        llm: LangChain LLM 实例
        prompt_manager: 可选的 PromptManager 实例

    Returns:
        moat_analyzer_node(state) -> dict 节点函数
    """
    pm = prompt_manager or get_prompt_manager()

    def moat_analyzer_node(state: dict) -> dict:
        """分析公司的经济护城河，返回结构化评估。"""
        company = state.get("company_of_interest", "Unknown")
        fundamentals_report = state.get("fundamentals_report", "Not available")
        market_report = state.get("market_report", "Not available")
        news_report = state.get("news_report", "Not available")

        try:
            prompt = pm.get_prompt(
                PromptNames.VALUATION_MOAT,
                variables={
                    "company": company,
                    "fundamentals_report": fundamentals_report,
                    "market_report": market_report,
                    "news_report": news_report,
                    "output_schema": json.dumps(MOAT_OUTPUT_SCHEMA, indent=2),
                },
            )

            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # 解析 JSON 输出
            moat = _parse_moat_response(content)
            return {"_moat_assessment": moat}

        except Exception as exc:
            logger.warning("Moat 分析失败 (%s): %s", company, exc)
            return {"_moat_assessment": dict(_DEFAULT_MOAT)}

    return moat_analyzer_node


def _parse_moat_response(content: str) -> dict:
    """从 LLM 响应中解析 MoatAssessment JSON。"""
    # 尝试提取 JSON
    start_idx = content.find("{")
    end_idx = content.rfind("}") + 1
    if start_idx != -1 and end_idx > start_idx:
        try:
            raw = json.loads(content[start_idx:end_idx])
            # 验证并规范化字段
            return _validate_moat(raw)
        except json.JSONDecodeError:
            pass

    logger.warning("无法从 LLM 响应中解析 Moat JSON，使用默认值")
    return dict(_DEFAULT_MOAT)


def _validate_moat(raw: dict) -> dict:
    """验证并规范化 LLM 输出的 moat 评估。"""
    valid_ratings = {"Wide", "Narrow", "None"}
    rating = raw.get("moat_rating", "None")
    if rating not in valid_ratings:
        # 模糊匹配
        rating_lower = rating.lower()
        if "wide" in rating_lower:
            rating = "Wide"
        elif "narrow" in rating_lower:
            rating = "Narrow"
        else:
            rating = "None"

    score = raw.get("sustainability_score", 5)
    if not isinstance(score, (int, float)):
        score = 5
    score = max(1, min(10, int(score)))

    sources = raw.get("moat_sources", [])
    if not isinstance(sources, list):
        sources = []

    reasoning = raw.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)

    return {
        "moat_rating": rating,
        "moat_sources": sources,
        "sustainability_score": score,
        "reasoning": reasoning,
    }
