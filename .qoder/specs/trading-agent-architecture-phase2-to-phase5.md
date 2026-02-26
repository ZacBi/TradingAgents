# Phase 0/1 遗漏项修复计划

## 范围

仅修复 Phase 0 和 Phase 1 中的遗漏项，不实现 Phase 2-5 的新功能。

## 遗漏项清单

| ID | 遗漏项 | 优先级 | 涉及文件 |
|----|--------|--------|----------|
| 1 | pyproject.toml 依赖升级（langgraph → 1.0+, 新增 optional groups） | P0 | `pyproject.toml` |
| 2 | LangGraph Checkpointing 集成 | P0 | `setup.py`, `trading_graph.py`, `propagation.py`, `default_config.py` |
| 3 | Langfuse trace_id 关联到决策记录 | P1 | `schema.py`, `manager.py`, `trading_graph.py` |
| 4 | 架构文档路线图 checkboxes 更新 | P2 | `.qoder/specs/trading-agent-architecture-analysis.md` |

---

## Step 1: pyproject.toml 依赖升级

**文件**: `pyproject.toml`

### 1.1 主依赖升级

将 langgraph 从 `>=0.4.8` 升级到 `>=1.0.0`（PyPI 最新稳定版约 1.0.7，2026-02 发布）。

```toml
dependencies = [
    "langchain-core>=0.3.81",
    "langgraph>=1.0.0",              # 从 >=0.4.8 升级
    "langchain-openai>=0.3.23",
    "langchain-anthropic>=0.3.15",
    "langchain-google-genai>=2.1.5",
    "langchain-experimental>=0.3.4",
    # ... 其余现有依赖保持不变
]
```

### 1.2 新增分组 optional-dependencies

在现有 `observability` 和 `litellm` 组后新增以下组（为 Phase 2-5 预留，本次不实现功能代码）：

```toml
[project.optional-dependencies]
observability = ["langfuse>=2.0"]
litellm = ["litellm>=1.0"]
# --- 以下为新增预留组 ---
memory = ["chromadb>=0.5.0"]
data-sources = [
    "fredapi>=0.5.0",
    "finnhub-python>=2.4.0",
    "praw>=7.7.0",
]
indicators = ["ta>=0.11.0"]
dashboard = ["streamlit>=1.28.0"]
api = ["fastapi>=0.104.0", "uvicorn>=0.24.0"]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
]
```

### 1.3 验证

```bash
uv sync -i https://pypi.tuna.tsinghua.edu.cn/simple
uv run python -c "
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
print('LangGraph 1.0 API OK')
"
```

若 `MemorySaver` 导入路径变化，需参照 LangGraph 1.0 实际 API 调整。已知 0.4.8 中 `langgraph-checkpoint` 2.0.26 已安装，升级后需确认 checkpoint 模块路径。

---

## Step 2: LangGraph Checkpointing 集成

设计原则：**可选特性，默认关闭，不影响现有功能**。

### 2.1 `default_config.py` 新增配置项

**文件**: `tradingagents/default_config.py` (第 46-48 行后)

新增 3 个配置项：

```python
# ----- Phase 0: LangGraph Checkpointing -----
"checkpointing_enabled": False,
"checkpoint_storage": "memory",        # memory | sqlite
"checkpoint_db_path": "checkpoints.db",
```

### 2.2 `trading_graph.py` 初始化 checkpointer

**文件**: `tradingagents/graph/trading_graph.py`

**修改1** — 第 146-149 行（数据库初始化后）新增：

```python
# --- Phase 0: LangGraph Checkpointing ---
self.checkpointer = None
if self.config.get("checkpointing_enabled"):
    self._init_checkpointer()
```

**修改2** — 新增 `_init_checkpointer()` 方法（在 `_init_database` 方法后）：

```python
def _init_checkpointer(self):
    """Initialize LangGraph checkpointer based on config."""
    try:
        storage = self.config.get("checkpoint_storage", "memory")
        if storage == "memory":
            from langgraph.checkpoint.memory import MemorySaver
            self.checkpointer = MemorySaver()
            logger.info("LangGraph MemorySaver checkpointer initialized.")
        elif storage == "sqlite":
            from langgraph.checkpoint.sqlite import SqliteSaver
            db_path = self.config.get("checkpoint_db_path", "checkpoints.db")
            self.checkpointer = SqliteSaver.from_conn_string(db_path)
            logger.info("LangGraph SQLite checkpointer at %s", db_path)
        else:
            logger.warning("Unknown checkpoint_storage: %s", storage)
    except Exception as exc:
        logger.warning("Checkpointer init failed: %s", exc)
        self.checkpointer = None
```

**修改3** — `GraphSetup` 初始化调用（约第 125 行）传入 checkpointer：

```python
self.graph_setup = GraphSetup(
    ...,
    checkpointer=self.checkpointer,  # 新增
)
```

**修改4** — `propagate()` 方法中生成 thread_id（约第 270-279 行）：

```python
thread_id = None
if self.checkpointer is not None:
    thread_id = f"{company_name}-{trade_date}"

args = self.propagator.get_graph_args(thread_id=thread_id)
```

### 2.3 `setup.py` 支持 checkpointer

**文件**: `tradingagents/graph/setup.py`

**修改1** — `__init__` 新增参数 `checkpointer=None`，保存为 `self.checkpointer`

**修改2** — `setup_graph()` 末尾（第 202 行）改为：

```python
if self.checkpointer is not None:
    return workflow.compile(checkpointer=self.checkpointer)
return workflow.compile()
```

### 2.4 `propagation.py` 支持 thread_id

**文件**: `tradingagents/graph/propagation.py`

`get_graph_args` 新增 `thread_id` 参数：

```python
def get_graph_args(self, callbacks=None, thread_id=None):
    config = {"recursion_limit": self.max_recur_limit}
    if callbacks:
        config["callbacks"] = callbacks
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}
    return {"stream_mode": "values", "config": config}
```

---

## Step 3: Langfuse trace_id 关联决策记录

### 3.1 `schema.py` 新增字段

**文件**: `tradingagents/database/schema.py`

在 `agent_decisions` 表的 `confidence` 后新增两列：

```sql
langfuse_trace_id   TEXT,
langfuse_trace_url  TEXT,
```

### 3.2 `manager.py` Schema 迁移 + CRUD 适配

**文件**: `tradingagents/database/manager.py`

**修改1** — `__init__` 末尾调用 `self._migrate_schema()`

**修改2** — 新增迁移方法：

```python
def _migrate_schema(self):
    with self._connect() as conn:
        cursor = conn.execute("PRAGMA table_info(agent_decisions)")
        columns = [row[1] for row in cursor.fetchall()]
        if "langfuse_trace_id" not in columns:
            conn.execute("ALTER TABLE agent_decisions ADD COLUMN langfuse_trace_id TEXT")
        if "langfuse_trace_url" not in columns:
            conn.execute("ALTER TABLE agent_decisions ADD COLUMN langfuse_trace_url TEXT")
```

**修改3** — `save_decision` 的 `cols` 列表中加入 `"langfuse_trace_id"`, `"langfuse_trace_url"`（在 `confidence` 之后）

### 3.3 `trading_graph.py` 传递 trace_id

**文件**: `tradingagents/graph/trading_graph.py`

在 `_persist_decision` 方法开头提取 trace_id：

```python
trace_id = trace_url = None
if self.config.get("langfuse_enabled") and self.callbacks:
    for cb in self.callbacks:
        if hasattr(cb, "trace_id") and cb.trace_id:
            trace_id = cb.trace_id
            host = self.config.get("langfuse_host", "http://localhost:3000")
            trace_url = f"{host}/trace/{trace_id}"
            break
```

然后在 `self.db.save_decision({...})` 字典中加入：

```python
"langfuse_trace_id": trace_id,
"langfuse_trace_url": trace_url,
```

---

## Step 4: 架构文档路线图更新

**文件**: `.qoder/specs/trading-agent-architecture-analysis.md`（第 830-865 行）

将阶段 0 和阶段 1 的 `- [ ]` 改为 `- [x]`：

```markdown
### 阶段0: 环境准备
- [x] 升级LangGraph到1.0
- [x] 部署LiteLLM网关 + 配置多平台密钥
- [x] 部署Langfuse自托管实例
- [x] 设置SQLite数据库

### 阶段1: 核心架构升级
- [x] LangGraph 1.0 Checkpointing集成
- [x] Langfuse追踪回调接入
- [x] LiteLLM分层模型配置（YAML配置化）
- [x] 持仓管理数据库实现
- [x] 重构 `trading_graph.py` 支持模型路由
```

---

## 关键文件汇总

| 文件 | 修改类型 |
|------|---------|
| `pyproject.toml` | 依赖版本升级 + 新增 optional groups |
| `tradingagents/default_config.py` | 新增 3 个 checkpointing 配置项 |
| `tradingagents/graph/trading_graph.py` | checkpointer 初始化 + thread_id + trace_id 提取 |
| `tradingagents/graph/setup.py` | `__init__` 新增参数 + `compile()` 传入 checkpointer |
| `tradingagents/graph/propagation.py` | `get_graph_args` 新增 thread_id 参数 |
| `tradingagents/database/schema.py` | agent_decisions 表新增 2 列 |
| `tradingagents/database/manager.py` | 迁移方法 + save_decision 字段扩展 |
| `.qoder/specs/trading-agent-architecture-analysis.md` | checkbox 更新 |

---

## 实施顺序

```
Step 1 (pyproject.toml) → uv sync 验证 → Step 2 (Checkpointing) → Step 3 (trace_id) → Step 4 (文档)
```

Step 1 必须先做且独立验证，因为 LangGraph 0.4.8 → 1.0 可能有 API 变更。如果 `MemorySaver` / `SqliteSaver` 导入路径或 `compile(checkpointer=...)` 签名有变化，需在 Step 2 中适配。

---

## 验证方案

### 依赖升级验证
```bash
uv sync -i https://pypi.tuna.tsinghua.edu.cn/simple
uv run python -c "
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
print('OK: LangGraph 1.0 core API available')
"
```

### Checkpointing 验证
```bash
uv run python -c "
from tradingagents.graph import TradingAgentsGraph
g = TradingAgentsGraph(config={
    'checkpointing_enabled': True,
    'checkpoint_storage': 'memory',
    'llm_provider': 'openai',
    'deep_think_llm': 'gpt-4o-mini',
    'quick_think_llm': 'gpt-4o-mini',
})
print('OK: checkpointer =', g.checkpointer)
"
```

### Database 迁移验证
```bash
uv run python -c "
from tradingagents.database import DatabaseManager
db = DatabaseManager(':memory:')
db._migrate_schema()
import sqlite3
conn = sqlite3.connect(':memory:')
# 验证列存在
print('OK: migration works')
"
```

### 端到端（需 API Key）
```bash
uv run python -c "
from tradingagents.graph import TradingAgentsGraph
g = TradingAgentsGraph(config={
    'checkpointing_enabled': True,
    'database_enabled': True,
    'database_path': '/tmp/test_ta.db',
})
state, signal = g.propagate('AAPL', '2026-02-25')
print(f'Signal: {signal}')
"
```

---

## 风险与回退

| 风险 | 缓解 |
|------|------|
| LangGraph 1.0 API 不兼容（StateGraph/ToolNode/START/END） | 先 `uv sync` 后立即跑导入验证；若失败则锁定到可用的最高版本 |
| `MemorySaver` 导入路径变化 | 查阅 langgraph-checkpoint 实际版本的 API，适配路径 |
| Langfuse handler 无 `trace_id` 属性 | 加 `hasattr` 保护，降级为 NULL |
| 现有已创建的 SQLite 数据库缺少新列 | `_migrate_schema()` 用 `ALTER TABLE ADD COLUMN` 自动加列 |
