# TradingAgents 使用文档

## 文档索引

### 环境与入门

0. [运行环境准备](./setup-environment.md) — 依赖安装、环境变量、数据库、Docker、验证步骤

### 核心功能

1. [Long-Run Agent使用指南](./long-run-agent.md)
   - 状态恢复
   - 定时调度
   - 健康监控
   - Prometheus指标

2. [自主交易使用指南](./autonomous-trading.md)
   - 交易接口配置
   - 订单执行
   - 风险控制
   - 持仓管理

### 扩展功能

3. [插件系统使用指南](./plugins.md)
   - 创建插件
   - 插件管理
   - 动态加载

4. [配置驱动流程使用指南](./workflow-config.md)
   - 配置文件格式
   - 配置选项
   - 程序化配置

## 快速开始

### 基础使用

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph

# 创建graph
graph = TradingAgentsGraph()

# 运行分析
final_state, signal = graph.propagate("AAPL", "2025-02-26")
print(f"Decision: {signal}")
```

### 启用Long-Run功能

```python
from tradingagents.graph.long_run import LongRunAgent

graph = TradingAgentsGraph(config={"checkpoint_storage": "postgres"})
long_run_agent = LongRunAgent(graph)
long_run_agent.start()
long_run_agent.schedule_daily_analysis("AAPL", hour=9, minute=30)
```

### 启用交易功能

```python
config = {
    "trading_enabled": True,
    "alpaca_api_key": "your_key",
    "alpaca_api_secret": "your_secret",
    "alpaca_paper": True,
}
graph = TradingAgentsGraph(config=config)
final_state, signal = graph.propagate("AAPL", "2025-02-26")
# 如果决策是交易，会自动执行
```

## 配置参考

### 完整配置示例

```python
config = {
    # 基础配置
    "selected_analysts": ["market", "social", "news", "fundamentals"],
    
    # Checkpoint配置
    "checkpoint_storage": "postgres",
    "checkpoint_postgres_url": "postgresql://user:password@localhost/tradingagents",
    "checkpointing_enabled": True,
    
    # 功能开关
    "valuation_enabled": True,
    "deep_research_enabled": False,
    "experts_enabled": True,
    "trading_enabled": True,
    
    # 交易配置
    "alpaca_api_key": "your_key",
    "alpaca_api_secret": "your_secret",
    "alpaca_paper": True,
    
    # 风险配置
    "risk_config": {
        "max_position_size": 0.20,
        "max_portfolio_risk": 0.15,
    },
    
    # 错误恢复配置
    "error_recovery_config": {
        "max_retries": 3,
        "retry_delay": 1.0,
    },
    
    # 插件配置
    "plugins_enabled": True,
    "plugin_dirs": ["./my_plugins"],
    
    # 工作流配置文件
    "workflow_config_file": "./workflow_config.json",
}
```

## 常见问题

### Q: 如何启用PostgreSQL checkpoint？

A: 设置 `checkpoint_storage: "postgres"` 并提供 `checkpoint_postgres_url`。

### Q: 如何启用交易功能？

A: 设置 `trading_enabled: True` 并提供Alpaca API凭证。

### Q: 如何添加自定义Analyst？

A: 使用插件系统，创建继承`BaseAnalyst`的类并注册为插件。

### Q: 如何配置风险限制？

A: 在`risk_config`中设置各种风险参数。

## 更多资源

- 架构设计文档：`docs/arch/10-comprehensive-architecture-redesign-spec.md`
- 实施总结：`docs/arch/12-implementation-summary.md`
- 问题分析：`docs/arch/11-implementation-review-and-issues.md`
