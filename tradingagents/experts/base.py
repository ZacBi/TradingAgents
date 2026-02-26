# TradingAgents/experts/base.py
"""Base types and protocols for the expert framework."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from typing_extensions import TypedDict


class ExpertOutput(TypedDict):
    """Structured output from an expert agent evaluation."""

    recommendation: Literal["BUY", "SELL", "HOLD"]
    confidence: float  # 0.0 - 1.0
    time_horizon: Literal["short_term", "medium_term", "long_term"]
    key_reasoning: list[str]  # 3-5 core arguments
    risks: list[str]  # Main risk factors
    position_suggestion: float  # Suggested position percentage 0-100


@dataclass
class ExpertProfile:
    """Profile defining an investment expert's characteristics and factory."""

    id: str  # Unique identifier: "buffett", "munger"
    name: str  # Display name: "Warren Buffett"
    philosophy: str  # Brief investment philosophy description
    applicable_sectors: list[str] = field(
        default_factory=lambda: ["any"]
    )  # Applicable industries
    market_cap_preference: Literal["large", "mid", "small", "any"] = "any"
    style: Literal["value", "growth", "momentum", "contrarian", "hybrid"] = "value"
    time_horizon: Literal["short", "medium", "long"] = "long"
    prompt_template: str = ""  # Expert-specific system prompt
    factory: Callable[..., Callable] | None = None  # Factory function reference

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, ExpertProfile):
            return self.id == other.id
        return False


# Expert output JSON schema for structured output parsing
EXPERT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation": {
            "type": "string",
            "enum": ["BUY", "SELL", "HOLD"],
            "description": "Investment recommendation",
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence level in the recommendation",
        },
        "time_horizon": {
            "type": "string",
            "enum": ["short_term", "medium_term", "long_term"],
            "description": "Recommended investment time horizon",
        },
        "key_reasoning": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
            "description": "Core arguments supporting the recommendation",
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Main risk factors to consider",
        },
        "position_suggestion": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Suggested position size as percentage of portfolio",
        },
    },
    "required": [
        "recommendation",
        "confidence",
        "time_horizon",
        "key_reasoning",
        "risks",
        "position_suggestion",
    ],
}
