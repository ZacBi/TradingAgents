"""LiteLLM client — routes through a LiteLLM proxy gateway.

Uses ChatOpenAI with the LiteLLM proxy base_url, so any model
identifier supported by LiteLLM (e.g. "gemini/gemini-3-flash",
"anthropic/claude-sonnet-4-5") can be passed through.
"""

import os
from typing import Any

from langchain_openai import ChatOpenAI

from .base_client import BaseLLMClient


class LiteLLMClient(BaseLLMClient):
    """Client that routes through a LiteLLM proxy gateway.

    The proxy exposes an OpenAI-compatible API at ``base_url``.
    The model name is forwarded as-is — LiteLLM handles provider routing.
    """

    DEFAULT_BASE_URL = "http://localhost:4000"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        **kwargs,
    ):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        """Return a ChatOpenAI instance pointing at the LiteLLM proxy."""
        llm_kwargs = {
            "model": self.model,
            "base_url": self.base_url or os.environ.get(
                "LITELLM_BASE_URL", self.DEFAULT_BASE_URL
            ),
        }

        api_key = os.environ.get("LITELLM_API_KEY", "sk-litellm")
        llm_kwargs["api_key"] = api_key

        for key in ("timeout", "max_retries", "callbacks"):
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        return ChatOpenAI(**llm_kwargs)

    def validate_model(self) -> bool:
        """LiteLLM accepts any model identifier — validation is done server-side."""
        return True
