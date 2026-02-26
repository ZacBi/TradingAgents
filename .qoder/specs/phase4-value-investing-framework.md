# Phase 4: Value Investing Framework - Implementation Plan

## Overview

在现有 TradingAgents LangGraph 管线中插入一个新的 **Valuation Stage**，位于 4 个 Analyst 之后、Bull/Bear 辩论之前。采用混合模式：Python 确定性计算（DCF、Graham Number）+ LLM Agent 定性分析（护城河评估）。

### Pipeline 变更

```
Before: ... Last Analyst Msg Clear → Bull Researcher → ...
After:  ... Last Analyst Msg Clear → Valuation Analyst → Bull Researcher → ...
```

---

## 1. 新增文件

### 1.1 `tradingagents/valuation/__init__.py` (~30 行)

模块导出 + `create_valuation_node()` 工厂函数。

### 1.2 `tradingagents/valuation/models.py` (~200 行)

纯 Python 计算引擎，无外部数学库依赖。

| 函数 | 功能 | 公式 |
|:---|:---|:---|
| `estimate_wacc(metrics)` | WACC 估算 | `(E/V)*Re + (D/V)*Rd*(1-T)`，Re = Rf + Beta * MRP |
| `calculate_dcf(metrics, config)` | DCF 三场景估值 | `Sum(FCF_t/(1+WACC)^t) + TV/(1+WACC)^n` |
| `calculate_graham_number(eps, bvps, price)` | Graham 防御性估值 | `sqrt(22.5 * EPS * BVPS)` |

**数据结构** (TypedDict):
```python
class FinancialMetrics(TypedDict, total=False):
    current_price: float
    free_cashflow: float
    operating_cashflow: float
    shares_outstanding: float
    trailing_eps: float
    book_value: float          # per share
    beta: float
    debt_to_equity: float
    revenue_growth: float
    earnings_growth: float
    profit_margins: float
    return_on_equity: float
    market_cap: float

class DCFResult(TypedDict):
    intrinsic_value: float
    current_price: float
    upside_pct: float
    wacc: float
    scenarios: dict            # {"bear": float, "base": float, "bull": float}

class GrahamNumberResult(TypedDict):
    graham_number: float
    current_price: float
    margin_of_safety: float    # (graham - price) / graham
    is_undervalued: bool

class ValuationResult(TypedDict):
    ticker: str
    analysis_date: str
    dcf: DCFResult | None
    graham: GrahamNumberResult | None
    moat: dict | None          # MoatAssessment from LLM
    recommendation: str        # "Strong Buy" | "Buy" | "Hold" | "Sell"
    confidence: str            # "High" | "Medium" | "Low"
    report: str                # Markdown formatted report
```

**边界处理**:
- FCF <= 0 → 跳过 DCF，标记 confidence = Low
- EPS <= 0 或 BVPS <= 0 → 跳过 Graham
- WACC <= terminal_growth → 强制 terminal_growth = WACC - 2%
- 所有计算跳过 → recommendation = "Hold", confidence = "Low"

### 1.3 `tradingagents/valuation/data_extractor.py` (~120 行)

从 `fundamentals_report` 文本中解析结构化财务指标。

```python
def extract_financial_metrics(
    ticker: str,
    fundamentals_report: str,
    trade_date: str,
) -> FinancialMetrics | None
```

**解析策略**:
1. 尝试在 fundamentals_report 中匹配 key-value 对（如 `freeCashflow: 99600000000`）
2. 使用 regex 匹配常见格式：`$99.6B`, `10.5%`, `6.13` 等
3. 若关键字段缺失（FCF/EPS/BVPS），直接调用 `yfinance_enhanced.get_valuation_metrics(ticker)` 补充
4. 数据清洗：去除货币符号、百分号，处理 B/M/K 单位

### 1.4 `tradingagents/valuation/moat_analyzer.py` (~130 行)

LLM Agent 节点，完全复用 Expert Agent 模式（参考 buffett.py）。

```python
def create_moat_analyzer(llm, prompt_manager=None) -> Callable:
    """工厂函数，返回 moat_analyzer_node(state) -> dict"""
```

**节点逻辑**:
1. 从 state 读取 `fundamentals_report`, `news_report`, `market_report`
2. `pm.get_prompt(PromptNames.VALUATION_MOAT, variables={...})`
3. `llm.invoke(prompt)` → 解析 JSON → MoatAssessment
4. 解析失败回退：`{"moat_rating": "None", "sustainability_score": 5, ...}`

**MoatAssessment 输出格式** (LLM JSON):
```json
{
  "moat_rating": "Wide|Narrow|None",
  "moat_sources": ["brand", "network_effect", ...],
  "sustainability_score": 8,
  "reasoning": "..."
}
```

### 1.5 `tradingagents/valuation/analyzer.py` (~200 行)

主编排器，串联 data_extractor + models + moat_analyzer。

```python
def create_valuation_node(llm, prompt_manager=None, config=None) -> Callable:
    """返回 valuation_node(state: AgentState) -> dict"""
```

**节点内部流程**:
```
1. extract_financial_metrics(ticker, fundamentals_report)
2. calculate_dcf(metrics, config)          # Python
3. calculate_graham_number(eps, bvps, price) # Python
4. moat_analyzer(state)                    # LLM call
5. synthesize_recommendation(dcf, graham, moat)
6. format_report(results) → markdown
7. return {"valuation_result": json.dumps(result)}
```

**综合决策规则**:

| DCF Upside | Graham MOS | Moat | Recommendation | Confidence |
|:---|:---|:---|:---|:---|
| >50% | >30% | Wide | Strong Buy | High |
| 20-50% | >10% | Narrow/Wide | Buy | High |
| 10-30% | Any | Any | Hold | Medium |
| <10% | <0% | None/Narrow | Sell | Medium |
| 部分数据缺失 | — | — | Hold | Low |

---

## 2. 修改现有文件

### 2.1 `tradingagents/agents/utils/agent_states.py`

添加一个字段：
```python
class AgentState(MessagesState):
    # ... existing fields ...
    # Phase 4: Valuation
    valuation_result: Annotated[str, "JSON serialized valuation analysis result"]
```

### 2.2 `tradingagents/default_config.py`

在 `DEFAULT_CONFIG` 末尾添加：
```python
# ----- Phase 4: Value Investing Framework -----
"valuation_enabled": True,
"valuation_dcf_projection_years": 5,
"valuation_terminal_growth_rate": 0.025,
"valuation_risk_free_rate": 0.04,
"valuation_market_risk_premium": 0.06,
"valuation_graham_safety_threshold": 0.30,
```

### 2.3 `tradingagents/prompts/registry.py`

```python
class PromptNames:
    # ... existing 17 ...
    VALUATION_MOAT = "valuation-moat"

PROMPT_LABELS[PromptNames.VALUATION_MOAT] = "valuation/moat"
ALL_PROMPT_NAMES.append(PromptNames.VALUATION_MOAT)
```

### 2.4 `tradingagents/prompts/fallback.py`

添加 `VALUATION_MOAT_TEMPLATE` (~600 字)，包含：
- 角色：经济护城河分析专家
- 输入变量：`{company}`, `{fundamentals_report}`, `{news_report}`, `{market_report}`
- 分析框架：品牌/网络效应/成本优势/切换成本/专利
- 输出要求：JSON 格式 MoatAssessment
- 注册到 `FALLBACK_TEMPLATES[PromptNames.VALUATION_MOAT]`

### 2.5 `tradingagents/graph/setup.py`

**GraphSetup.__init__()** 新增参数：
```python
def __init__(self, ..., config=None, prompt_manager=None):
    self.config = config or {}
    self.prompt_manager = prompt_manager
```

**setup_graph()** 修改：
```python
# 1. 若 valuation_enabled，创建节点
if self.config.get("valuation_enabled", True):
    from tradingagents.valuation import create_valuation_node
    valuation_node = create_valuation_node(
        llm=self.quick_thinking_llm,
        prompt_manager=self.prompt_manager,
        config=self.config,
    )
    workflow.add_node("Valuation Analyst", valuation_node)

# 2. 修改最后一个 Analyst 的 Msg Clear 出边
if i == len(selected_analysts) - 1:
    if self.config.get("valuation_enabled", True):
        workflow.add_edge(current_clear, "Valuation Analyst")  # 改为指向 Valuation
    else:
        workflow.add_edge(current_clear, "Bull Researcher")    # 保持原逻辑

# 3. Valuation → Bull Researcher (无条件边)
if self.config.get("valuation_enabled", True):
    workflow.add_edge("Valuation Analyst", "Bull Researcher")
```

### 2.6 `tradingagents/graph/trading_graph.py`

**GraphSetup 初始化时传入 config 和 prompt_manager**：
```python
self.graph_setup = GraphSetup(
    ...,
    config=self.config,
    prompt_manager=self.prompt_manager,
)
```

**_persist_decision()** 添加 valuation_result：
```python
decision_data = {
    ...,
    "valuation_result": final_state.get("valuation_result", ""),
}
```

**_log_state()** 添加 valuation_result 到日志。

### 2.7 `tradingagents/database/schema.py` (或 database.py)

在 `agent_decisions` 表 CREATE TABLE 语句中添加 `valuation_result TEXT` 列。

---

## 3. Implementation Order

| Step | Task | Files | Depends On |
|:---|:---|:---|:---|
| 1 | 数据结构 + 模块骨架 | `valuation/__init__.py`, `models.py` (TypedDict only) | — |
| 2 | AgentState 扩展 | `agent_states.py` | — |
| 3 | 配置项 | `default_config.py` | — |
| 4 | Prompt 注册 | `registry.py`, `fallback.py` | — |
| 5 | 数据提取器 | `data_extractor.py` | Step 1 |
| 6 | DCF + Graham 计算引擎 | `models.py` (计算函数) | Step 1, 5 |
| 7 | Moat Analyzer LLM Agent | `moat_analyzer.py` | Step 4 |
| 8 | 主编排器 | `analyzer.py` | Step 5, 6, 7 |
| 9 | Graph 集成 | `setup.py`, `trading_graph.py` | Step 2, 3, 8 |
| 10 | 数据库扩展 | `database/schema.py`, `trading_graph.py` | Step 9 |
| 11 | 单元测试 | `tests/valuation/` | Step 6, 7, 8 |

---

## 4. Verification Plan

### 4.1 单元测试 (`tests/valuation/`)

```bash
uv run -i https://pypi.tuna.tsinghua.edu.cn/simple python -m pytest tests/valuation/ -v
```

**test_models.py**:
- `test_dcf_positive_fcf`: 已知 FCF=100B, growth=10%, WACC=8.5% → 验证内在价值在合理范围
- `test_dcf_negative_fcf`: FCF=-50B → 返回 None
- `test_graham_positive`: EPS=6.13, BVPS=3.85 → graham_number ≈ 36.05
- `test_graham_negative_eps`: EPS=-2 → 返回 None
- `test_wacc_estimation`: 给定 beta/debt_equity → WACC 在 5%-15% 区间

**test_data_extractor.py**:
- Mock fundamentals_report 文本 → 验证解析出正确的 FinancialMetrics

**test_moat_analyzer.py**:
- Mock LLM 返回 → 验证 JSON 解析为 MoatAssessment
- Mock LLM 返回无效 JSON → 验证 fallback 行为

**test_analyzer.py**:
- 综合决策规则覆盖：5 种组合场景 → 验证 recommendation 和 confidence

### 4.2 集成验证

```bash
# 1. 导入测试
uv run python -c "from tradingagents.valuation import create_valuation_node; print('OK')"

# 2. 配置测试
uv run python -c "from tradingagents.default_config import DEFAULT_CONFIG; print(DEFAULT_CONFIG.get('valuation_enabled'))"

# 3. 禁用估值回归测试
# 设置 valuation_enabled=False，验证原流程不受影响
```

### 4.3 端到端（需要 LLM API Key）

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
graph = TradingAgentsGraph(config={"valuation_enabled": True})
state, signal = graph.propagate("AAPL", "2025-01-15")
print(state.get("valuation_result"))  # 应有 DCF/Graham/Moat 结果
```

---

## 5. Critical Files Summary

**新增** (5 files):
- `tradingagents/valuation/__init__.py`
- `tradingagents/valuation/models.py`
- `tradingagents/valuation/data_extractor.py`
- `tradingagents/valuation/moat_analyzer.py`
- `tradingagents/valuation/analyzer.py`

**修改** (7 files):
- `tradingagents/agents/utils/agent_states.py` — 添加 `valuation_result` 字段
- `tradingagents/default_config.py` — 添加 6 个配置项
- `tradingagents/prompts/registry.py` — 注册 `VALUATION_MOAT`
- `tradingagents/prompts/fallback.py` — 添加 Moat Prompt 模板
- `tradingagents/graph/setup.py` — 插入 Valuation 节点到工作流
- `tradingagents/graph/trading_graph.py` — 传递 config/prompt_manager，扩展持久化
- `tradingagents/database/` — 添加 valuation_result 列
