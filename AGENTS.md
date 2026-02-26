# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

TradingAgents is a multi-agent LLM-powered financial trading framework. It uses LangGraph/LangChain for agent orchestration, yfinance for market data, and supports multiple LLM providers (OpenAI, Google, Anthropic, xAI, OpenRouter, Ollama).

### Python & package management

- **Python 3.13+** is required (`requires-python = ">=3.13"`).
- **uv** is the package manager. The lockfile is `uv.lock`.
- Install: `uv sync --extra dev --extra testing`

### Running services

| Service | Command | Notes |
|:---|:---|:---|
| CLI (interactive) | `uv run tradingagents analyze` | Requires at least one LLM API key |
| CLI (help) | `uv run tradingagents --help` | No API key needed |
| Backtest | `uv run tradingagents backtest --ticker AAPL --start 2024-01-01 --end 2024-12-31` | Needs prior decision data |
| Dashboard | `uv run streamlit run dashboard/app.py` | Requires `--extra dashboard` |

### Lint / Test / Build

- **Lint:** `uv run ruff check .` (22 pre-existing warnings in the codebase; these are not blocking)
- **Tests:** `uv run pytest` (51 unit tests in `tests/valuation/`)
- **Type check:** `uv run mypy tradingagents/`
- **Build:** `uv build`

### Non-obvious caveats

- The `google-generativeai not available for deep research` warning at import time is benign; it just means the optional `google-generativeai` package (for deep research mode) is not installed.
- `TradingAgentsGraph()` initialization requires an LLM API key (e.g. `OPENAI_API_KEY`). Without one, the constructor raises `OpenAIError`. Data-layer functions (`route_to_vendor`) work without any API key.
- Data functions in `tradingagents/agents/utils/` are LangChain `@tool`-decorated, so they are `StructuredTool` objects. Call them with `.invoke({"symbol": ..., "start_date": ..., "end_date": ...})` or use `route_to_vendor()` directly from `tradingagents.dataflows.interface`.
- The `tests/` directory only has tests under `tests/valuation/`. No test files exist in the root `tests/` directory.
- Default database is SQLite (no external DB needed). PostgreSQL is optional via `--extra postgres` and `docker-compose.yml`.
- `redis` is listed as a dependency but has zero usage in the codebase.
