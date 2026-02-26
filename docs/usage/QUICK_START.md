# TradingAgents 快速开始指南

## 5分钟快速开始

### 1. 基础分析

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph

# 创建graph（使用默认配置）
graph = TradingAgentsGraph()

# 运行分析
final_state, signal = graph.propagate("AAPL", "2025-02-26")
print(f"Decision: {signal}")
```

### 2. 启用Long-Run功能

```python
from tradingagents.graph.long_run import LongRunAgent

# 配置PostgreSQL checkpoint
config = {
    "checkpoint_storage": "postgres",
    "checkpoint_postgres_url": "postgresql://user:password@localhost/tradingagents",
}

graph = TradingAgentsGraph(config=config)
long_run_agent = LongRunAgent(graph)

# 启动并调度
long_run_agent.start()
long_run_agent.schedule_daily_analysis("AAPL", hour=9, minute=30)
```

### 3. 启用自主交易

```python
config = {
    "trading_enabled": True,
    "alpaca_api_key": "your_key",
    "alpaca_api_secret": "your_secret",
    "alpaca_paper": True,  # 使用paper trading
    "risk_config": {
        "max_position_size": 0.20,
    },
}

graph = TradingAgentsGraph(config=config)
final_state, signal = graph.propagate("AAPL", "2025-02-26")
# 如果决策是交易，会自动执行订单
```

### 4. 使用配置文件

创建 `workflow_config.json`:

```json
{
  "analysts": ["market", "news"],
  "trading_enabled": true,
  "trading_config": {
    "alpaca_api_key": "your_key",
    "alpaca_api_secret": "your_secret",
    "alpaca_paper": true
  }
}
```

使用配置：

```python
config = {
    "workflow_config_file": "./workflow_config.json",
}
graph = TradingAgentsGraph(config=config)
```

## 完整示例

### 生产环境配置

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.graph.long_run import LongRunAgent

# 完整配置
config = {
    # Checkpoint
    "checkpoint_storage": "postgres",
    "checkpoint_postgres_url": "postgresql://user:password@localhost/tradingagents",
    
    # 交易
    "trading_enabled": True,
    "alpaca_api_key": os.getenv("ALPACA_API_KEY"),
    "alpaca_api_secret": os.getenv("ALPACA_API_SECRET"),
    "alpaca_paper": False,  # 生产环境使用live trading
    
    # 风险控制
    "risk_config": {
        "max_position_size": 0.15,
        "max_portfolio_risk": 0.10,
        "stop_loss_pct": 0.05,
    },
    
    # 错误恢复
    "error_recovery_config": {
        "max_retries": 3,
    },
}

# 创建graph和long-run agent
graph = TradingAgentsGraph(config=config)
long_run_agent = LongRunAgent(graph)

# 启动
long_run_agent.start()

# 调度多个股票
for ticker in ["AAPL", "GOOGL", "MSFT"]:
    long_run_agent.schedule_daily_analysis(ticker, hour=9, minute=30)

# 监控健康状态
import time
while True:
    health = long_run_agent.get_health_status()
    print(f"Health: {health['status']}")
    time.sleep(60)  # 每分钟检查一次
```

## 下一步

- 阅读 [Long-Run Agent使用指南](./long-run-agent.md)
- 阅读 [自主交易使用指南](./autonomous-trading.md)
- 阅读 [插件系统使用指南](./plugins.md)
- 阅读 [配置驱动流程使用指南](./workflow-config.md)
