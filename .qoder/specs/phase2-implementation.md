# Phase 2: 数据源升级 - 实施方案

## 概述

在现有多供应商路由架构 (`route_to_vendor` + `VENDOR_METHODS` + `TOOLS_CATEGORIES`) 基础上，新增三类数据源：

1. **YFinance 增强**: 财报日期、估值指标、机构持仓 → 绑定到现有 fundamentals 分析师
2. **FRED 宏观经济**: CPI、GDP、利率、失业率、M2 → 新增宏观工具集
3. **长桥 Longport**: 实时行情、K线数据（港美A股）→ 新增实时行情工具集

---

## Step 1: YFinance 增强

### 1.1 新建 `tradingagents/dataflows/yfinance_enhanced.py`

3 个函数，沿用现有 `y_finance.py` 的模式（`yf.Ticker` → 格式化字符串）:

```python
def get_earnings_dates(ticker: str) -> str
    # yf.Ticker(ticker).earnings_dates → CSV with Date, EPS Estimate, Reported EPS, Surprise(%)
    
def get_valuation_metrics(ticker: str) -> str
    # yf.Ticker(ticker).info → 提取 P/E, P/B, EV/EBITDA, PEG, Price/Sales, Price/FCF,
    #   EV/Revenue, enterprise_value, market_cap 等估值指标
    # 返回 "# Valuation Metrics for {ticker}\n\nP/E Ratio: ...\n..."

def get_institutional_holders(ticker: str) -> str
    # yf.Ticker(ticker).institutional_holders → CSV (Holder, Shares, Date Reported, % Out, Value)
```

### 1.2 新建 `tradingagents/agents/utils/valuation_data_tools.py`

3 个 @tool 函数，遵循 `fundamental_data_tools.py` 的模式：

```python
@tool
def get_earnings_dates(ticker: Annotated[str, "ticker symbol"]) -> str:
    return route_to_vendor("get_earnings_dates", ticker)

@tool
def get_valuation_metrics(ticker: Annotated[str, "ticker symbol"]) -> str:
    return route_to_vendor("get_valuation_metrics", ticker)

@tool
def get_institutional_holders(ticker: Annotated[str, "ticker symbol"]) -> str:
    return route_to_vendor("get_institutional_holders", ticker)
```

### 1.3 修改 `tradingagents/dataflows/interface.py`

- 新增 import `yfinance_enhanced` 的 3 个函数
- `TOOLS_CATEGORIES` 新增 `"valuation_data"` category
- `VENDOR_METHODS` 新增 3 条 yfinance 映射

### 1.4 修改 `tradingagents/agents/utils/agent_utils.py`

新增 import valuation_data_tools 的 3 个 @tool

### 1.5 修改 `tradingagents/graph/trading_graph.py`

在 `_create_tool_nodes()` 的 `"fundamentals"` ToolNode 中追加 3 个新工具:

```python
"fundamentals": ToolNode([
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_earnings_dates,        # 新增
    get_valuation_metrics,     # 新增
    get_institutional_holders, # 新增
]),
```

同时在文件顶部新增对应的 import。

### 1.6 修改 `tradingagents/default_config.py`

`data_vendors` 新增:
```python
"valuation_data": "yfinance",
```

---

## Step 2: FRED 宏观经济数据

### 2.1 新建 `tradingagents/dataflows/fred.py`

可选依赖模式（`try: from fredapi import Fred`），从环境变量 `FRED_API_KEY` 或 config 读取 key。

```python
def get_fred_series(series_id: str, start_date: str, end_date: str) -> str
    # 通用函数，返回 "# {series_id} from FRED\n# Date range: ...\n\nDate,Value\n..."

def get_cpi(start_date: str, end_date: str) -> str           # CPIAUCSL
def get_gdp(start_date: str, end_date: str) -> str           # GDP
def get_interest_rate(rate_type: str, start_date: str, end_date: str) -> str
    # rate_type: federal_funds(FEDFUNDS), treasury_10y(DGS10), treasury_2y(DGS2)
def get_unemployment_rate(start_date: str, end_date: str) -> str  # UNRATE
def get_m2_money_supply(start_date: str, end_date: str) -> str    # M2SL
```

### 2.2 新建 `tradingagents/agents/utils/macro_data_tools.py`

5 个 @tool 函数:

```python
@tool get_cpi_data(start_date, end_date) -> str
@tool get_gdp_data(start_date, end_date) -> str
@tool get_interest_rate_data(rate_type, start_date, end_date) -> str
@tool get_unemployment_data(start_date, end_date) -> str
@tool get_m2_data(start_date, end_date) -> str
```

### 2.3 修改 `tradingagents/dataflows/interface.py`

- 新增 import fred 函数（用 try-except 保护，缺包时不阻塞其他功能）
- `TOOLS_CATEGORIES` 新增 `"macro_data"` category
- `VENDOR_METHODS` 新增 5 条 fred 映射
- `VENDOR_LIST` 新增 `"fred"`

### 2.4 修改 `tradingagents/agents/utils/agent_utils.py`

新增 import macro_data_tools 的 5 个 @tool

### 2.5 修改 `tradingagents/graph/trading_graph.py`

在 `_create_tool_nodes()` 的 `"news"` ToolNode 中追加宏观工具（新闻分析师同时关注宏观）:

```python
"news": ToolNode([
    get_news,
    get_global_news,
    get_insider_transactions,
    get_cpi_data,          # 新增
    get_gdp_data,          # 新增
    get_interest_rate_data,# 新增
    get_unemployment_data, # 新增
    get_m2_data,           # 新增
]),
```

### 2.6 修改 `tradingagents/default_config.py`

```python
"data_vendors" 新增: "macro_data": "fred",
新增 API key 配置: "fred_api_key": None,  # or FRED_API_KEY env var
```

### 2.7 修改 `pyproject.toml`

`fredapi` 已在 `[data-sources]` optional 中，无需修改。

---

## Step 3: 长桥 Longport 实时行情

### 3.1 新建 `tradingagents/dataflows/longport_api.py`

可选依赖模式（`try: from longport.openapi import QuoteContext, Config`）。

```python
def _get_quote_context() -> QuoteContext:
    # 从环境变量 LONGPORT_APP_KEY/APP_SECRET/ACCESS_TOKEN 或 config 读取
    # 缓存 context 实例

def _normalize_symbol(symbol: str, market: str) -> str:
    # US: "AAPL" → "AAPL.US", HK: "700" → "0700.HK", CN: "000001" → "000001.SZ"

def get_longport_quote(symbol: str, market: str = "US") -> str
    # QuoteContext.quote([symbol]) → 单行快照
    # 返回: "# Realtime Quote for {symbol}\n\nLast: ... Change: ... Volume: ..."

def get_longport_kline(symbol: str, period: str, start_date: str, end_date: str, market: str = "US") -> str
    # QuoteContext.candlesticks(symbol, period, count, adjust_type) → CSV
    # period: "1min","5min","15min","30min","60min","day","week","month"
    # 返回格式与 yfinance 对齐: "Date,Open,High,Low,Close,Volume\n..."
```

### 3.2 新建 `tradingagents/agents/utils/realtime_data_tools.py`

2 个 @tool 函数:

```python
@tool get_realtime_quote(symbol, market="US") -> str
@tool get_kline_data(symbol, period, start_date, end_date, market="US") -> str
```

### 3.3 修改 `tradingagents/dataflows/interface.py`

- 新增 import longport_api 函数（try-except 保护）
- `TOOLS_CATEGORIES` 新增 `"realtime_data"` category
- `VENDOR_METHODS` 新增 2 条 longport 映射
- `VENDOR_LIST` 新增 `"longport"`

### 3.4 修改 `tradingagents/agents/utils/agent_utils.py`

新增 import realtime_data_tools 的 2 个 @tool

### 3.5 修改 `tradingagents/graph/trading_graph.py`

在 `_create_tool_nodes()` 的 `"market"` ToolNode 中追加实时数据工具:

```python
"market": ToolNode([
    get_stock_data,
    get_indicators,
    get_realtime_quote,  # 新增
    get_kline_data,      # 新增
]),
```

### 3.6 修改 `tradingagents/default_config.py`

```python
"data_vendors" 新增: "realtime_data": "longport",
新增 API key 配置:
    "longport_app_key": None,        # or LONGPORT_APP_KEY env var
    "longport_app_secret": None,     # or LONGPORT_APP_SECRET env var
    "longport_access_token": None,   # or LONGPORT_ACCESS_TOKEN env var
```

### 3.7 修改 `pyproject.toml`

在 `data-sources` optional 中新增:
```
"longport>=1.0.0",
```

---

## Step 4: 更新架构文档 checkbox

修改 `trading-agent-architecture-analysis.md` Phase 2 的 checkbox 标记为 `[x]`。

---

## 文件变更汇总

| 操作 | 文件路径 | 变更内容 |
|:-----|:---------|:---------|
| **新建** | `tradingagents/dataflows/yfinance_enhanced.py` | 3 个 YFinance 增强函数 |
| **新建** | `tradingagents/dataflows/fred.py` | FRED 宏观数据函数（可选依赖） |
| **新建** | `tradingagents/dataflows/longport_api.py` | Longport 实时行情函数（可选依赖） |
| **新建** | `tradingagents/agents/utils/valuation_data_tools.py` | 3 个 @tool（估值/财报/持仓） |
| **新建** | `tradingagents/agents/utils/macro_data_tools.py` | 5 个 @tool（CPI/GDP/利率/失业率/M2） |
| **新建** | `tradingagents/agents/utils/realtime_data_tools.py` | 2 个 @tool（实时行情/K线） |
| **修改** | `tradingagents/dataflows/interface.py` | 3 个新 category + vendor 映射 |
| **修改** | `tradingagents/default_config.py` | 3 个新 vendor category + 4 个 API key |
| **修改** | `tradingagents/agents/utils/agent_utils.py` | import 10 个新 @tool |
| **修改** | `tradingagents/graph/trading_graph.py` | 扩展 _create_tool_nodes() 3 组 ToolNode + import |
| **修改** | `pyproject.toml` | data-sources 新增 longport 依赖 |
| **修改** | `.qoder/specs/trading-agent-architecture-analysis.md` | Phase 2 checkbox |

---

## 验证方案

### V1: 依赖安装
```bash
uv sync --extra data-sources
# 验证 fredapi, longport 都装好
```

### V2: 模块导入
```python
# 验证所有新模块可导入
from tradingagents.dataflows.yfinance_enhanced import get_earnings_dates, get_valuation_metrics, get_institutional_holders
from tradingagents.dataflows.fred import get_cpi, get_gdp, get_interest_rate, get_unemployment_rate, get_m2_money_supply
from tradingagents.dataflows.longport_api import get_longport_quote, get_longport_kline
from tradingagents.agents.utils.valuation_data_tools import get_earnings_dates, get_valuation_metrics, get_institutional_holders
from tradingagents.agents.utils.macro_data_tools import get_cpi_data, get_gdp_data, get_interest_rate_data, get_unemployment_data, get_m2_data
from tradingagents.agents.utils.realtime_data_tools import get_realtime_quote, get_kline_data
```

### V3: 数据获取测试
```python
# YFinance 增强（无需 API key）
from tradingagents.dataflows.interface import route_to_vendor
print(route_to_vendor("get_valuation_metrics", "AAPL"))
print(route_to_vendor("get_earnings_dates", "AAPL"))
print(route_to_vendor("get_institutional_holders", "AAPL"))

# FRED（需 FRED_API_KEY 环境变量）
print(route_to_vendor("get_cpi_data", "2024-01-01", "2025-01-01"))

# Longport（需 LONGPORT_* 环境变量）
print(route_to_vendor("get_realtime_quote", "AAPL", "US"))
```

### V4: ToolNode 集成
```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
# 验证 TradingAgentsGraph 初始化不报错（工具绑定正确）
# 需要 LLM API key，可通过 mock 或实际调用验证
```

### V5: 路由测试
```python
from tradingagents.dataflows.interface import get_category_for_method, TOOLS_CATEGORIES
# 验证所有新方法都能找到 category
for method in ["get_valuation_metrics", "get_earnings_dates", "get_institutional_holders",
               "get_cpi_data", "get_gdp_data", "get_interest_rate_data",
               "get_unemployment_data", "get_m2_data",
               "get_realtime_quote", "get_kline_data"]:
    cat = get_category_for_method(method)
    print(f"{method} → {cat}")
```

---

## 实施顺序

1. **Step 1 (YFinance)** → 优先，无外部 API 依赖，可立即测试
2. **Step 2 (FRED)** → 次优先，需要 FRED_API_KEY
3. **Step 3 (Longport)** → 最后，需要 Longport token
4. **Step 4 (文档)** → 最后更新 checkbox

每个 Step 完成后立即运行对应验证，不等全部完成。
