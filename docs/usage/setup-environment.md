# 运行环境准备（Environment Setup）

本文档为 README 的补充，说明如何准备运行 TradingAgents 的完整环境（依赖、环境变量、数据库、Docker 等）。

## 1. 前置要求

- **Python 3.13+**
- **uv**（推荐）：[安装 uv](https://docs.astral.sh/uv/getting-started/installation/) 后可用 `uv sync` 管理依赖与虚拟环境；未安装 uv 时可用 pip + 系统 Python/conda。

## 2. 克隆与安装依赖

```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

使用 **uv**（推荐）或 pip 安装核心依赖：

```bash
# 使用 uv：自动创建 .venv 并安装依赖
uv sync

# 或使用 pip（需先创建并激活虚拟环境）
pip install -e .
```

## 3. 可选依赖（按需安装）

| 功能 | 命令 | 说明 |
|------|------|------|
| Streamlit 看板 | `uv sync --extra dashboard` | 查看决策、NAV 曲线与统计 |
| Langfuse 可观测 | `uv sync --extra observability` | 链路追踪与 Prompt 管理 |
| PostgreSQL | `uv sync --extra postgres` | Checkpoint / Store 使用 Postgres |
| 更多数据源 | `uv sync --extra data-sources` | FRED、Finnhub、Reddit、Longport 等 |
| LiteLLM 网关 | `uv sync --extra litellm` | 使用 LiteLLM 统一代理多模型时安装 |
| 开发/测试 | `uv sync --extra dev` | pytest、ruff、mypy、pre-commit 等（贡献者） |

示例：同时安装看板与可观测性：

```bash
uv sync --extra dashboard --extra observability
```

## 4. 环境变量与 API 密钥

复制示例配置并填写密钥（项目会通过 `python-dotenv` 自动加载 `.env`）：

```bash
cp .env.example .env
# 编辑 .env，填入你要使用的 API Key
```

**至少配置一个 LLM 提供方**（否则分析无法调用模型）：

| 提供方 | 环境变量 | 说明 |
|--------|----------|------|
| OpenAI | `OPENAI_API_KEY` | 默认推荐 |
| Google Gemini | `GOOGLE_API_KEY` | |
| Anthropic Claude | `ANTHROPIC_API_KEY` | |
| xAI (Grok) | `XAI_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | |
| 本地模型 | 无需 Key，配置 `llm_provider: "ollama"` | 需本地运行 Ollama |
| LiteLLM 网关 | 见下方「LiteLLM 网关」 | 需先安装 optional、再单独起代理并配置 |

使用 **Alpha Vantage** 作为数据源时需设置 `ALPHA_VANTAGE_API_KEY`；默认数据源为 yfinance，无需额外 Key。

**LiteLLM 网关（可选）**  
LiteLLM 在本项目中作为**统一代理**：TradingAgents 将请求发往 LiteLLM 代理（OpenAI 兼容接口），由代理转发到 OpenAI/Anthropic/Google 等。

- **安装**：`uv sync --extra litellm`（安装与代理通信所需的依赖）。
- **单独起代理**：LiteLLM 代理需**单独进程**运行（非本项目启动）。例如本地安装 [LiteLLM](https://docs.litellm.ai/docs/) 后：
  ```bash
  litellm --config /path/to/litellm_config.yaml
  ```
  或使用官方 Docker 镜像、自建 config 配置各厂商 API Key 与路由。代理默认监听 `http://localhost:4000`。
- **本项目的配置**：在 config 或 `.env` 中设置：
  - `llm_provider`: 设为 `litellm`（否则不会走 LiteLLM 客户端）。
  - `LITELLM_BASE_URL`：代理地址，默认 `http://localhost:4000`。
  - `LITELLM_API_KEY`：代理的 API Key（若代理启用了鉴权），默认 `sk-litellm`。
  配置中的 `litellm_base_url`（或 `backend_url` 当 provider 为 litellm 时）会指向该代理。

可选：Langfuse 可观测性需配置 `LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`（见 `.env.example`）。使用 Docker 的 `observability` profile 时 Langfuse 为自托管，访问 http://localhost:3000。

**其他配置**：根目录 `model_routing.yaml` 可配置按角色选择不同 LLM（需在 config 中开启 `model_routing_enabled`）。完整环境变量说明见 `.env.example`。

## 5. 数据库（Database）

- **默认：SQLite**  
  无需单独安装。首次运行分析或回测时会在项目目录下生成 `tradingagents.db`（路径由 `TRADINGAGENTS_DB_PATH` 控制，默认 `tradingagents.db`）。用于存储决策记录、回测结果与 Dashboard 展示。

- **可选：PostgreSQL**  
  适用于生产或需要与 LangGraph Checkpoint/Store 共用数据库时。需安装可选依赖并配置连接：

  ```bash
  uv sync --extra postgres
  ```

  在 `.env` 中设置（或使用下方 Docker 启动后再填）：

  ```bash
  TRADINGAGENTS_POSTGRES_URL=postgresql://用户名:密码@host:5432/数据库名
  ```

  若使用统一 Postgres，可只设 `TRADINGAGENTS_POSTGRES_URL`，Checkpoint/Store 会复用该连接（见 `.env.example` 与 `tradingagents.config.settings`）。

- **环境变量摘要**（详见 `.env.example`）：

  | 变量 | 说明 |
  |------|------|
  | `TRADINGAGENTS_DB_PATH` | SQLite 文件路径，默认 `tradingagents.db` |
  | `TRADINGAGENTS_POSTGRES_URL` | PostgreSQL 连接 URL（可选） |
  | `TRADINGAGENTS_CHECKPOINT_STORAGE` | `memory` / `sqlite` / `postgres` |
  | `TRADINGAGENTS_CHECKPOINT_SQLITE_PATH` | Checkpoint 使用 SQLite 时的文件路径 |

使用 **PostgreSQL** 时，若需执行建表或迁移，可参考 `tradingagents/database` 下的 Alembic 配置（`alembic.ini` 与 migrations）。

## 6. Docker（可选）

项目提供 `docker-compose.yml`，用于本地启动 **PostgreSQL（含 pgvector）**，以及可选的 **pgAdmin**、**Langfuse**。

**仅启动 Postgres（推荐先只起数据库）：**

```bash
docker compose up -d
```

首次启动时会执行 `scripts/init-db.sql`（创建 pgvector 等扩展）。默认连接信息：

- 用户/库：`tradingagents`，密码：`tradingagents_dev`，端口：`5432`
- 可在 `.env` 中设置 `POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`、`POSTGRES_PORT` 覆盖

**应用连接 Docker 中的 Postgres：**  
在 `.env` 中配置（与上面变量一致）：

```bash
TRADINGAGENTS_POSTGRES_URL=postgresql://tradingagents:tradingagents_dev@localhost:5432/tradingagents
```

**可选服务（按 profile 启动）：**

| Profile | 服务 | 命令 |
|---------|------|------|
| （默认） | 仅 Postgres | `docker compose up -d` |
| `admin` | Postgres + pgAdmin | `docker compose --profile admin up -d`，pgAdmin 默认 http://localhost:5050 |
| `observability` | Postgres + Langfuse | `docker compose --profile observability up -d`，Langfuse 默认 http://localhost:3000 |

停止并删除数据卷：`docker compose down -v`。更多说明见 `docker-compose.yml` 顶部注释。

## 7. 验证环境

```bash
# 检查 CLI 是否可用
uv run tradingagents --help

# 运行一次交互式分析（会提示选择 ticker、日期、LLM 等）
uv run tradingagents analyze
```

## 8. 回测与看板补充说明

- **回测数据来源**：`uv run tradingagents backtest` 的决策数据需先通过 `tradingagents analyze` 并启用数据库持久化写入 SQLite，或自行准备符合列格式（ticker, trade_date, final_decision）的 CSV。
- **看板**：Dashboard 读取的数据库路径由 `TRADINGAGENTS_DB_PATH` 控制，默认 `tradingagents.db`。

更多架构设计、使用指南（Long-Run、自主交易、插件等）见 **`docs/arch/`** 与 **`docs/usage/`** 目录。
