# tests/valuation/test_moat_analyzer.py
"""Moat Analyzer 单元测试（不依赖真实 LLM 调用）。"""

import pytest

from tradingagents.valuation.moat_analyzer import (
    _parse_moat_response,
    _validate_moat,
    _DEFAULT_MOAT,
)


class TestParseMoatResponse:
    def test_valid_json(self):
        content = '''Some preamble text...
{
    "moat_rating": "Wide",
    "moat_sources": ["brand", "network_effect"],
    "sustainability_score": 9,
    "reasoning": "Strong brand power and dominant ecosystem."
}
Some trailing text'''
        result = _parse_moat_response(content)
        assert result["moat_rating"] == "Wide"
        assert "brand" in result["moat_sources"]
        assert result["sustainability_score"] == 9
        assert "Strong brand" in result["reasoning"]

    def test_no_json_returns_default(self):
        result = _parse_moat_response("This is plain text without JSON.")
        assert result["moat_rating"] == "None"
        assert result["sustainability_score"] == 5

    def test_invalid_json_returns_default(self):
        result = _parse_moat_response('{"moat_rating": "Wide", broken}')
        assert result["moat_rating"] == "None"

    def test_empty_content(self):
        result = _parse_moat_response("")
        assert result == dict(_DEFAULT_MOAT)


class TestValidateMoat:
    def test_valid_input(self):
        raw = {
            "moat_rating": "Narrow",
            "moat_sources": ["cost_advantage"],
            "sustainability_score": 7,
            "reasoning": "Low cost producer",
        }
        result = _validate_moat(raw)
        assert result["moat_rating"] == "Narrow"
        assert result["sustainability_score"] == 7

    def test_fuzzy_rating_matching(self):
        """模糊匹配大小写变体。"""
        raw = {"moat_rating": "wide moat", "moat_sources": [], "sustainability_score": 8, "reasoning": ""}
        assert _validate_moat(raw)["moat_rating"] == "Wide"

        raw["moat_rating"] = "NARROW"
        assert _validate_moat(raw)["moat_rating"] == "Narrow"

        raw["moat_rating"] = "something_else"
        assert _validate_moat(raw)["moat_rating"] == "None"

    def test_score_clamping(self):
        """分数超范围时应被截断。"""
        raw = {"moat_rating": "Wide", "moat_sources": [], "sustainability_score": 15, "reasoning": ""}
        assert _validate_moat(raw)["sustainability_score"] == 10

        raw["sustainability_score"] = -3
        assert _validate_moat(raw)["sustainability_score"] == 1

    def test_missing_fields_use_defaults(self):
        result = _validate_moat({})
        assert result["moat_rating"] == "None"
        assert result["sustainability_score"] == 5
        assert result["moat_sources"] == []
        assert result["reasoning"] == ""

    def test_non_list_sources(self):
        raw = {"moat_rating": "Wide", "moat_sources": "brand", "sustainability_score": 8, "reasoning": ""}
        result = _validate_moat(raw)
        assert result["moat_sources"] == []
