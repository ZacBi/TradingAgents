# tests/valuation/test_analyzer.py
"""估值分析编排器与综合决策逻辑单元测试。"""

import pytest

from tradingagents.valuation.analyzer import _synthesize_recommendation


class TestSynthesizeRecommendation:
    """测试综合决策规则引擎。"""

    def test_strong_buy_all_positive(self):
        """高 DCF upside + 高 Graham MOS + Wide Moat → Strong Buy。"""
        dcf = {"upside_pct": 60.0, "intrinsic_value": 320, "current_price": 200, "wacc": 0.085, "scenarios": {}}
        graham = {"graham_number": 300, "current_price": 200, "margin_of_safety": 0.35, "is_undervalued": True}
        moat = {"moat_rating": "Wide", "moat_sources": ["brand"], "sustainability_score": 9, "reasoning": "Strong brand"}

        rec, conf = _synthesize_recommendation(dcf, graham, moat)
        assert rec == "Strong Buy"
        assert conf == "High"

    def test_buy_moderate_signals(self):
        """中等 DCF upside + 中等 Graham MOS + Narrow Moat → Buy。"""
        dcf = {"upside_pct": 35.0, "intrinsic_value": 135, "current_price": 100, "wacc": 0.09, "scenarios": {}}
        graham = {"graham_number": 120, "current_price": 100, "margin_of_safety": 0.17, "is_undervalued": True}
        moat = {"moat_rating": "Narrow", "moat_sources": ["cost"], "sustainability_score": 6, "reasoning": ""}

        rec, conf = _synthesize_recommendation(dcf, graham, moat)
        assert rec == "Buy"

    def test_sell_negative_signals(self):
        """负 DCF upside + 负 Graham MOS + No Moat → Sell。"""
        dcf = {"upside_pct": -15.0, "intrinsic_value": 85, "current_price": 100, "wacc": 0.10, "scenarios": {}}
        graham = {"graham_number": 70, "current_price": 100, "margin_of_safety": -0.43, "is_undervalued": False}
        moat = {"moat_rating": "None", "moat_sources": [], "sustainability_score": 2, "reasoning": ""}

        rec, conf = _synthesize_recommendation(dcf, graham, moat)
        assert rec == "Sell"

    def test_hold_when_all_missing(self):
        """所有指标缺失 → Hold, Low confidence。"""
        rec, conf = _synthesize_recommendation(None, None, None)
        assert rec == "Hold"
        assert conf == "Low"

    def test_partial_data_dcf_only(self):
        """仅有 DCF → 中等 confidence。"""
        dcf = {"upside_pct": 25.0, "intrinsic_value": 125, "current_price": 100, "wacc": 0.09, "scenarios": {}}

        rec, conf = _synthesize_recommendation(dcf, None, None)
        assert rec in ("Hold", "Buy")
        assert conf == "Medium"

    def test_partial_data_graham_only(self):
        """仅有 Graham → 中等 confidence。"""
        graham = {"graham_number": 150, "current_price": 100, "margin_of_safety": 0.33, "is_undervalued": True}

        rec, conf = _synthesize_recommendation(None, graham, None)
        assert rec in ("Buy", "Strong Buy")
        assert conf == "Medium"

    def test_moat_bonus_effect(self):
        """Wide Moat 对中等信号有提升作用。"""
        dcf = {"upside_pct": 15.0, "intrinsic_value": 115, "current_price": 100, "wacc": 0.09, "scenarios": {}}
        graham = {"graham_number": 105, "current_price": 100, "margin_of_safety": 0.05, "is_undervalued": True}

        # 无 Moat
        rec_no_moat, _ = _synthesize_recommendation(dcf, graham, None)

        # Wide Moat
        moat = {"moat_rating": "Wide", "moat_sources": ["brand"], "sustainability_score": 9, "reasoning": ""}
        rec_moat, _ = _synthesize_recommendation(dcf, graham, moat)

        # Moat 加成后推荐应不低于无 Moat
        ranking = {"Sell": 0, "Hold": 1, "Buy": 2, "Strong Buy": 3}
        assert ranking[rec_moat] >= ranking[rec_no_moat]
