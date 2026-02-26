"""Token cost estimation for LLM usage.

Uses a simple per-model price table (USD per 1K tokens) to estimate
cost from token counts. When model_name is unknown, uses default rates
aligned with typical GPT-4o-mini / Gemini Flash–level pricing.
"""

from typing import Any

# Default USD per 1K tokens (input, output) for unknown/mixed models.
# Roughly aligned with GPT-4o-mini / Gemini Flash tier (2024–2025).
DEFAULT_INPUT_PER_1K = 0.00015   # $0.15 / 1M input
DEFAULT_OUTPUT_PER_1K = 0.0006   # $0.60 / 1M output

# Optional: model-specific rates (can be loaded from YAML later).
MODEL_RATES: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
    "gpt-4o": {"input_per_1k": 0.0025, "output_per_1k": 0.01},
    "gpt-4.5-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
    "gpt-5-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
    "gemini-2.0-flash": {"input_per_1k": 0.000075, "output_per_1k": 0.0003},
    "gemini-3-flash": {"input_per_1k": 0.000075, "output_per_1k": 0.0003},
    "claude-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
}


def estimate_cost(
    tokens_in: int,
    tokens_out: int,
    model_name: str | None = None,
    rates: dict[str, dict[str, float]] | None = None,
) -> float:
    """Estimate cost in USD from token counts.

    Args:
        tokens_in: Input token count.
        tokens_out: Output token count.
        model_name: Optional model identifier; if None or unknown, default rates are used.
        rates: Optional override map model_name -> {"input_per_1k", "output_per_1k"}.

    Returns:
        Estimated cost in USD.
    """
    rates = rates or MODEL_RATES
    if model_name and model_name in rates:
        r = rates[model_name]
        in_per_1k = r.get("input_per_1k", DEFAULT_INPUT_PER_1K)
        out_per_1k = r.get("output_per_1k", DEFAULT_OUTPUT_PER_1K)
    else:
        in_per_1k = DEFAULT_INPUT_PER_1K
        out_per_1k = DEFAULT_OUTPUT_PER_1K

    cost_in = (tokens_in / 1000.0) * in_per_1k
    cost_out = (tokens_out / 1000.0) * out_per_1k
    return round(cost_in + cost_out, 6)


def get_default_rates() -> dict[str, Any]:
    """Return default rate constants for documentation or config export."""
    return {
        "default_input_per_1k": DEFAULT_INPUT_PER_1K,
        "default_output_per_1k": DEFAULT_OUTPUT_PER_1K,
        "model_rates": dict(MODEL_RATES),
    }
