# Prompt Management 集成方案 (Langfuse)

## 概述

将项目中所有硬编码的 Prompt 模板迁移至 Langfuse Prompt Management，实现：
- 版本控制与回滚
- A/B 测试能力
- 热加载（无需重启）
- 集中化管理界面

## 现状分析

### Prompt 模板分布

| 类别 | 文件数 | 模板数 | 当前存储方式 |
|:-----|:-------|:-------|:-------------|
| Experts | 5 | 5 | `*_PROMPT_TEMPLATE` 常量 |
| Analysts | 4 | 4 | 函数内 `system_message` |
| Researchers | 2 | 2 | 函数内 f-string |
| Risk Mgmt | 3 | 3 | 函数内 f-string |
| Managers | 2 | 2 | 函数内 f-string |
| Trader | 1 | 1 | 函数内硬编码 |
| **合计** | **17** | **17** | - |

### 已有 Langfuse 集成

- `tradingagents/observability/langfuse_handler.py` - Tracing 回调
- `langfuse>=2.0` 依赖已安装
- 数据库已支持 `langfuse_trace_id` 字段

---

## 架构设计

### 1. 新增模块结构

```
tradingagents/
├── prompts/
│   ├── __init__.py           # 导出 PromptManager
│   ├── manager.py            # Langfuse Prompt 管理器
│   ├── registry.py           # Prompt 名称注册表
│   └── fallback.py           # 本地 fallback 模板
```

### 2. PromptManager 核心类

```python
class PromptManager:
    """
    Langfuse Prompt 管理器
    - 从 Langfuse 拉取 prompt 模板
    - 支持本地 fallback
    - 缓存 + 热加载
    """
    
    def __init__(self, config: dict):
        self._langfuse = Langfuse(...)
        self._cache: dict[str, PromptTemplate] = {}
        self._cache_ttl = config.get("prompt_cache_ttl", 300)  # 5分钟
    
    def get_prompt(
        self,
        name: str,
        version: Optional[str] = None,
        variables: Optional[dict] = None,
    ) -> str:
        """
        获取并编译 prompt
        1. 检查缓存
        2. 从 Langfuse 拉取
        3. 若失败，使用本地 fallback
        4. 填充变量
        """
```

### 3. Prompt 命名规范

| Agent 类型 | Prompt 名称 | Langfuse Label |
|:-----------|:------------|:---------------|
| Buffett Expert | `expert-buffett` | expert/buffett |
| Munger Expert | `expert-munger` | expert/munger |
| Lynch Expert | `expert-lynch` | expert/lynch |
| Livermore Expert | `expert-livermore` | expert/livermore |
| Graham Expert | `expert-graham` | expert/graham |
| Market Analyst | `analyst-market` | analyst/market |
| Social Analyst | `analyst-social` | analyst/social |
| News Analyst | `analyst-news` | analyst/news |
| Fundamentals Analyst | `analyst-fundamentals` | analyst/fundamentals |
| Bull Researcher | `researcher-bull` | researcher/bull |
| Bear Researcher | `researcher-bear` | researcher/bear |
| Research Manager | `manager-research` | manager/research |
| Risk Manager | `manager-risk` | manager/risk |
| Aggressive Debator | `risk-aggressive` | risk/aggressive |
| Conservative Debator | `risk-conservative` | risk/conservative |
| Neutral Debator | `risk-neutral` | risk/neutral |
| Trader | `trader-main` | trader/main |

### 4. 配置项扩展

```python
# default_config.py
DEFAULT_CONFIG = {
    # ... 现有配置 ...
    
    # ----- Prompt Management (Langfuse) -----
    "prompt_management_enabled": True,
    "prompt_cache_ttl": 300,          # 秒，0=禁用缓存
    "prompt_fallback_enabled": True,  # 本地 fallback
    "prompt_version": None,           # None=production, 或指定版本号
}
```

---

## 实施步骤

### Step 1: 创建 PromptManager 模块

**新建文件**:
- `tradingagents/prompts/__init__.py`
- `tradingagents/prompts/manager.py`
- `tradingagents/prompts/registry.py`
- `tradingagents/prompts/fallback.py`

**fallback.py** 保存所有现有 prompt 模板作为本地备份。

### Step 2: 重构 Agent 调用方式

**Before**:
```python
# experts/investors/buffett.py
prompt = BUFFETT_PROMPT_TEMPLATE.format(...)
response = llm.invoke(prompt)
```

**After**:
```python
# experts/investors/buffett.py
prompt = prompt_manager.get_prompt(
    "expert-buffett",
    variables={
        "market_report": market_report,
        "sentiment_report": sentiment_report,
        ...
    }
)
response = llm.invoke(prompt)
```

### Step 3: 初始化 Langfuse Prompts

提供脚本将现有 prompt 批量上传到 Langfuse：
```bash
python -m tradingagents.prompts.init_langfuse
```

### Step 4: 集成到 TradingAgentsGraph

```python
# trading_graph.py
def __init__(self, ...):
    # ...
    self._init_prompt_manager()

def _init_prompt_manager(self):
    if self.config.get("prompt_management_enabled"):
        from tradingagents.prompts import PromptManager
        self.prompt_manager = PromptManager(self.config)
    else:
        self.prompt_manager = None
```

---

## 关键修改文件

| 文件 | 修改内容 |
|:-----|:---------|
| `tradingagents/prompts/manager.py` | 新建：PromptManager 核心实现 |
| `tradingagents/prompts/registry.py` | 新建：Prompt 名称常量 |
| `tradingagents/prompts/fallback.py` | 新建：本地 fallback 模板 |
| `tradingagents/default_config.py` | 新增 prompt 管理配置项 |
| `tradingagents/graph/trading_graph.py` | 初始化 PromptManager |
| `tradingagents/experts/investors/*.py` | 使用 PromptManager 获取 prompt |
| `tradingagents/agents/analysts/*.py` | 使用 PromptManager 获取 prompt |
| `tradingagents/agents/researchers/*.py` | 使用 PromptManager 获取 prompt |
| `tradingagents/agents/risk_mgmt/*.py` | 使用 PromptManager 获取 prompt |
| `tradingagents/agents/managers/*.py` | 使用 PromptManager 获取 prompt |
| `tradingagents/agents/trader/trader.py` | 使用 PromptManager 获取 prompt |

---

## 验证方案

### 1. 单元测试
```bash
# 测试 PromptManager
python -c "
from tradingagents.prompts import PromptManager
pm = PromptManager({'prompt_management_enabled': True})
prompt = pm.get_prompt('expert-buffett', variables={'market_report': 'test'})
print(prompt[:100])
"
```

### 2. Fallback 测试
```bash
# 禁用 Langfuse，验证 fallback
python -c "
from tradingagents.prompts import PromptManager
pm = PromptManager({'prompt_management_enabled': True, 'langfuse_enabled': False})
prompt = pm.get_prompt('expert-buffett', variables={...})
assert 'Warren Buffett' in prompt
"
```

### 3. 端到端测试
```bash
# 完整流程测试
python -c "
from tradingagents import TradingAgentsGraph
graph = TradingAgentsGraph(config={'prompt_management_enabled': True})
state, signal = graph.propagate('AAPL', '2024-01-15')
print(signal)
"
```

---

## 风险与缓解

| 风险 | 缓解措施 |
|:-----|:---------|
| Langfuse 不可用 | 本地 fallback + 缓存 |
| Prompt 版本不一致 | 支持锁定版本号 |
| 热加载性能开销 | TTL 缓存（默认 5 分钟） |
| 迁移期间兼容性 | `prompt_management_enabled` 开关 |
