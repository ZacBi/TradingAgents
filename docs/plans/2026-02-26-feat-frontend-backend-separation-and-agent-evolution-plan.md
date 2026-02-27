---
title: feat: Frontend–Backend Separation & Agent System Evolution
type: feat
status: active
date: 2026-02-26
---

# feat: Frontend–Backend Separation & Agent System Evolution

## Overview

TradingAgents 已完成一次大规模架构重构（Phase 1–4），目前已经具备：

- 完整的多 Agent 决策流程（Analyst → Researcher → Trader → Risk → Portfolio）
- Long-Run 能力（定时调度、checkpoint 恢复、健康监控）
- 自主交易能力（TradingInterface + Alpaca 适配器 + RiskController + OrderExecutor + PositionManager）
- 观测性能力（Langfuse、Prometheus、MetricsCollector）
- CLI + Streamlit Dashboard 形态的本地单用户使用体验

本规划基于以下三份架构文档进行整合，**不得遗漏关键信息**：

- `docs/arch/13-frontend-backend-separation-evaluation.md`
- `docs/arch/14-industry-research-trading-agents.md`
- `docs/arch/15-project-positioning-and-evolution.md`

目标是：

1. 明确 TradingAgents 魔改后的 **项目定位** 和与业界框架的 **差异/不足**
2. 在此基础上，设计一个 **前后端分离 + 功能/模块进化** 的综合升级方案
3. 输出可执行的阶段性实现计划（API 设计、页面设计、技术栈与里程碑）

## Problem Statement

### 当前状态

- **架构层面**
  - 后端核心：`TradingAgentsGraph` + LangGraph 流程构建 + StateManager + RecoveryEngine + TradingInterface + RiskController + Order/PositionManager。
  - 持久化：PostgreSQL/SQLite + SQLAlchemy ORM，支持 agent_decisions、positions、trades、daily_nav 等。
  - 长期运行：`TradingAgentScheduler`（APScheduler）、HealthMonitor、Prometheus MetricsCollector。
  - 观测性：Langfuse 集成、错误恢复与重试机制、lineage 数据溯源。
- **交互层面**
  - CLI（Typer + Rich）：强交互、适合本地使用，但体验偏“工程师向”。
  - Streamlit Dashboard：只能查看历史决策与 NAV，非完整 Web App，不支持丰富交互和实时体验。
- **使用场景**
  - 当前仅 **单用户** 使用，未来也定位为 **单用户** 工具（不考虑多租户、多用户权限系统）。

### 痛点与不足

结合三份文档与业界调研：

1. **用户体验不足**
   - 没有真正的前后端分离 Web App，只能通过 CLI 和 Streamlit。
   - 无法在浏览器中方便地查看：“我的信息（持仓、盈亏、NAV）+ 实时信息流 + Agent 决策输出”。

2. **实时性不足**
   - 实时数据流（行情、新闻、指标）依赖轮询或 CLI 输出，没有统一 WebSocket 通道推送到前端。

3. **学习/记忆能力有限**
   - 已有 Memory Store + FinancialSituationMemory，但更多用于检索而非长期“经验”积累和反馈闭环。
   - 与 RL 框架（TensorTrade）相比，没有“策略学习/优化”的路径规划。

4. **生态对比中的短板**
   - 与 Hummingbot、Magents 相比，多交易所/多策略管理较弱。
   - 与 OpenBB、PortfolioManager 相比，前端 UI、数据可视化和数据源聚合能力尚未补足。

## Proposed Solution

在保持 TradingAgents **“单用户 + 可解释 + 生产级多 Agent LLM 交易系统”** 的核心定位下，进行有选择性的进化：

1. **前后端分离 MVP**
   - 后端：FastAPI + SQLAlchemy + FastAPI WebSocket，暴露围绕单用户“自己账户”的核心 API（持仓/NAV、决策、信息流）。
   - 前端：React + Material-UI + ECharts，提供 4 个核心页面：
     - Dashboard（总览页）
     - Positions（持仓页）
     - Decisions（决策列表 + 决策详情页）
     - Datafeed（信息流页）
   - 仅做 **单用户**，不引入多租户/权限系统，认证可暂时省略或用简单 API Key。

2. **数据能力增强（选取性进化）**
   - 在保持 yfinance / Alpha Vantage 的前提下，评估集成 OpenBB 作为统一数据访问层。
   - 对接 WebSocket 数据源（如 Alpaca、Binance）或 OpenBB 中的实时源，统一到 DataAccessor + 后端 WebSocket 服务。

3. **记忆与学习能力增强（中期）**
   - 基于已有 Memory Store 和 FinancialSituationMemory，补齐“决策结果反馈 → 经验写回 → 下次调用参考”的闭环。
   - 不走 RL 大修改路线，而是在 LLM + Memory 体系上做轻量增强。

4. **回测与分析能力增强（中期）**
   - 集成 vectorbt 或增强现有 backtest 模块，使决策结果可以更方便地做统计分析与可视化展示（前端图表）。

5. **扩展能力（可选）**
   - 若未来有需要，引入 Hummingbot / python-binance 等组件，扩展到多交易所/多资产，但仍保持“单用户使用”的前提。

## Technical Approach

### Architecture

#### 后端总体架构

- **核心引擎层**（已存在）
  - `TradingAgentsGraph`（多 Agent 决策工作流）
  - `StateManager`、`RecoveryEngine`、`ErrorRecovery`
  - `TradingInterface` + `AlpacaAdapter` + `RiskController` + `Order/PositionManager`
  - `DatabaseManager`（SQLAlchemy）

- **API/Web 层（新增）**
  - FastAPI 应用：
    - REST API：`/api/v1/portfolio`, `/api/v1/positions`, `/api/v1/decisions`, `/api/v1/datafeed` …
    - WebSocket：`/ws/stream`（统一推送持仓、决策、信息流事件）
  - 与现有 `DatabaseManager`、`TradingAgentsGraph` 解耦：API 层只依赖 Service 层接口。

- **Service 层（建议抽象）**
  - `PortfolioService`：封装 portfolio & positions 读取逻辑，基于 `DatabaseManager`。
  - `DecisionService`：封装决策读取 / 触发逻辑，调用 `TradingAgentsGraph` 或查询历史 `AgentDecision`。
  - `DatafeedService`：封装数据流（历史 + 实时）获取逻辑，集成 DataAccessor / OpenBB / yfinance。
  - `StreamService`：统一向 WebSocket Manager 推送事件。

- **前端层**
  - React 18 + TypeScript。
  - Material-UI 用于布局、表格、卡片等组件。
  - ECharts（或 Nivo）用于 NAV 曲线、持仓分布、决策统计图。

### API 设计（简化版）

#### Portfolio & Positions

- `GET /api/v1/portfolio`：总资产、现金、持仓价值、总 PnL、daily return。
- `GET /api/v1/positions`：持仓列表（ticker, quantity, avg_cost, current_price, unrealized_pnl …）。
- `GET /api/v1/nav?start_date=&end_date=&limit=`：NAV 历史序列。

#### Decisions

- `GET /api/v1/decisions?ticker=&start_date=&end_date=&limit=`：决策列表。
- `GET /api/v1/decisions/{id}`：决策详情（包含各 Analyst/Researcher/Trader/Risk 的输出）。
- 可选：`POST /api/v1/analysis/start`：触发一次新的分析 + 交易流程。

#### Datafeed

- `GET /api/v1/datafeed?type=&ticker=&limit=`：历史数据流（新闻、行情、指标）。
- `GET /api/v1/datafeed/stream` WebSocket：实时推送 `datafeed:new` 事件。

### WebSocket 事件

- `position:update`：单个持仓或持仓集合变化。
- `portfolio:update`：总览数据变化。
- `decision:new`：新增决策。
- `datafeed:new`：新数据流条目。

## Implementation Phases

### Phase 1: 核心 API & WebSocket 层（1–2 周）

**目标**：在不破坏现有 CLI/Streamlit 的前提下，建立最小可用 FastAPI 后端。

**任务**：

1. FastAPI 应用骨架（`tradingagents/api/`，按模块拆分 router）。
2. Service 抽象：`PortfolioService`、`DecisionService`、`DatafeedService` 等。
3. REST API 实现：落实 `portfolio/positions/decisions/datafeed` 相关接口。
4. WebSocket 实现：`ConnectionManager` + 事件广播。
5. 启动脚本与基础文档更新。

### Phase 2: 前端 MVP（1–2 周）

**目标**：用 React 为单用户构建 4 个核心页面，并打通 API。

**任务**：

1. 在 `web/` 下初始化 Vite + React + TS 项目。
2. 实现 Dashboard / Positions / Decisions / Datafeed 页面。
3. 集成 WebSocket 客户端，实现实时更新。

### Phase 3: 数据与实时能力增强（2–3 周）

**目标**：强化数据源与实时性。

**任务**：

1. 评估并集成 OpenBB 作为统一数据访问层（可选）。
2. 接入真实 WebSocket 数据源（Alpaca/Binance/OpenBB 等）。
3. 完善 Datafeed 持久化与历史回放。

### Phase 4: 记忆与学习能力增强（3–4 周）

**目标**：让 Agent 从历史决策表现中“学习”。

**任务**：

1. 完善 Memory 使用：写入决策经验、按情景检索。
2. 建立决策结果反馈闭环。
3. 在前端增加“复盘/经验”视图。

### Phase 5: 回测与扩展能力（2–3 周，可选）

**目标**：增强策略验证能力并为未来扩展留接口。

**任务**：

1. 集成 vectorbt 或增强现有 backtest。
2. 前端展示回测结果图表。
3. 预留多交易所扩展接口（Hummingbot/python-binance）。

## Acceptance Criteria

### 功能性要求

- 提供可用的 REST API（Portfolio/Positions/Decisions/Datafeed），并有 FastAPI 自动文档。
- 提供稳定的 WebSocket 通道，推送 portfolio/positions/decisions/datafeed 更新。
- 前端四大页面实现并可实时刷新数据。
- 不破坏现有 CLI 与 Streamlit Dashboard。

### 非功能性要求

- 延迟：本地 WebSocket 推送端到端延迟在可接受范围（< 200ms）。
- 可靠性：外部数据源异常时具备基本重试/降级逻辑。
- 安全性：单用户本地模式可不启用认证；若公网暴露，则需至少支持 API Key。
- 可维护性：API、Service 层和前端组件结构清晰，符合现有架构设计原则。

## Dependencies & Risks

### 依赖

- 现有 LangGraph + TradingAgentsGraph + DatabaseManager 已稳定。
- APScheduler、Prometheus、Alpaca 等组件已集成并可用。
- 新增依赖：FastAPI、Uvicorn、React、Material-UI、ECharts 等（需通过 uv/pnpm/yarn 管理）。

### 风险与缓解

- 外部数据源不稳定：通过 DataAccessor + 缓存 + 多源兜底缓解。
- 前后端复杂度上升：保持单用户、不引入权限/租户系统，严格控制 scope。
- 时间精力有限：按 Phase 优先级执行，先保证 Phase 1/2 完成。

## References & Research

- 内部文档：
  - `docs/arch/13-frontend-backend-separation-evaluation.md`
  - `docs/arch/14-industry-research-trading-agents.md`
  - `docs/arch/15-project-positioning-and-evolution.md`
  - `docs/arch/10-comprehensive-architecture-redesign-spec.md`
  - `docs/arch/12-implementation-summary.md`
- 外部项目与文档：
  - PortfolioManager（Flask + React + SQLAlchemy）
  - FastAPI Trading App（FastAPI + WebSocket）
  - OpenBB（统一数据源接口）
  - FastAPI WebSocket 官方文档
  - Alpaca WebSocket/Market Data 文档

