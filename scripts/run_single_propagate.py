"""Run a single ticker/date propagation. Prefer: uv run tradingagents analyze."""

from dotenv import load_dotenv

from tradingagents.config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

load_dotenv()

config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = "gpt-5-mini"
config["quick_think_llm"] = "gpt-5-mini"
config["max_debate_rounds"] = 1
config["data_vendors"] = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
}

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)
