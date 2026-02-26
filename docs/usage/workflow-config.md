# 配置驱动流程使用指南

## 概述

配置驱动流程允许通过配置文件定义工作流结构，而无需修改代码，提供更大的灵活性和可配置性。

## 快速开始

### 1. 创建配置文件

创建 `workflow_config.json`:

```json
{
  "analysts": ["market", "social", "news", "fundamentals"],
  "valuation_enabled": true,
  "deep_research_enabled": false,
  "experts_enabled": true,
  "trading_enabled": true,
  "workflow": {
    "debate_rounds": 2,
    "risk_rounds": 2
  },
  "trading_config": {
    "alpaca_api_key": "your_key",
    "alpaca_api_secret": "your_secret",
    "alpaca_paper": true
  },
  "risk_config": {
    "max_position_size": 0.20,
    "max_portfolio_risk": 0.15
  }
}
```

或使用YAML格式 `workflow_config.yaml`:

```yaml
analysts:
  - market
  - social
  - news
  - fundamentals

valuation_enabled: true
deep_research_enabled: false
experts_enabled: true
trading_enabled: true

workflow:
  debate_rounds: 2
  risk_rounds: 2

trading_config:
  alpaca_api_key: your_key
  alpaca_api_secret: your_secret
  alpaca_paper: true

risk_config:
  max_position_size: 0.20
  max_portfolio_risk: 0.15
```

### 2. 使用配置文件

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph

config = {
    "workflow_config_file": "./workflow_config.json",
}

graph = TradingAgentsGraph(config=config)
# 工作流会根据配置文件自动设置
```

## 配置选项

### 基础配置

```json
{
  "analysts": ["market", "social", "news", "fundamentals"],
  "valuation_enabled": true,
  "deep_research_enabled": false,
  "experts_enabled": true,
  "trading_enabled": false
}
```

### 工作流配置

```json
{
  "workflow": {
    "debate_rounds": 3,
    "risk_rounds": 3,
    "max_recur_limit": 100
  }
}
```

### 交易配置

```json
{
  "trading_config": {
    "alpaca_api_key": "your_key",
    "alpaca_api_secret": "your_secret",
    "alpaca_paper": true,
    "alpaca_base_url": "https://paper-api.alpaca.markets"
  }
}
```

### 风险配置

```json
{
  "risk_config": {
    "max_position_size": 0.20,
    "max_portfolio_risk": 0.15,
    "max_single_stock_exposure": 0.30,
    "max_sector_exposure": 0.40,
    "stop_loss_pct": 0.05,
    "take_profit_pct": 0.10,
    "max_daily_loss": 0.05,
    "margin_requirement": 0.50
  }
}
```

### 错误恢复配置

```json
{
  "error_recovery_config": {
    "max_retries": 3,
    "retry_delay": 1.0,
    "backoff_multiplier": 2.0,
    "retryable_errors": ["transient", "rate_limit", "network"]
  }
}
```

### Checkpoint配置

```json
{
  "checkpoint_storage": "postgres",
  "checkpoint_postgres_url": "postgresql://user:password@localhost/tradingagents",
  "checkpointing_enabled": true
}
```

### 插件配置

```json
{
  "plugins_enabled": true,
  "plugin_dirs": [
    "./my_plugins",
    "./custom_agents"
  ]
}
```

## 程序化配置

```python
from tradingagents.config.workflow_config import WorkflowConfig, WorkflowBuilder

# 创建配置
workflow_config = WorkflowConfig({
    "analysts": ["market", "news"],
    "trading_enabled": True,
    "workflow": {
        "debate_rounds": 2,
    },
})

# 应用到graph
graph = TradingAgentsGraph(config={})
workflow_builder = WorkflowBuilder(workflow_config)
workflow_builder.apply_to_graph_setup(graph.graph_setup)
```

## 配置验证

```python
from tradingagents.config.workflow_config import WorkflowConfig

try:
    config = WorkflowConfig.from_file("workflow_config.json")
    print("Configuration valid")
except Exception as e:
    print(f"Configuration error: {e}")
```

## 默认配置

```python
from tradingagents.config.workflow_config import WorkflowConfig

# 获取默认配置
default_config = WorkflowConfig.default_config()

# 查看默认值
print(default_config.get_analysts())
print(default_config.is_feature_enabled("trading"))
```

## 环境变量覆盖

配置文件中的值可以被环境变量覆盖：

```python
import os

config = {
    "workflow_config_file": "./workflow_config.json",
    # 环境变量可以覆盖配置
    "alpaca_api_key": os.getenv("ALPACA_API_KEY"),
}
```

## 最佳实践

1. **使用版本控制**：将配置文件纳入版本控制
2. **环境分离**：为不同环境（dev, staging, prod）使用不同配置
3. **敏感信息**：API密钥等敏感信息使用环境变量
4. **配置验证**：启动时验证配置有效性
5. **文档化**：为自定义配置项提供文档

## 故障排查

### 配置文件未找到

```python
try:
    config = WorkflowConfig.from_file("workflow_config.json")
except FileNotFoundError:
    print("Configuration file not found")
    # 使用默认配置
    config = WorkflowConfig.default_config()
```

### 配置解析错误

```python
try:
    config = WorkflowConfig.from_file("workflow_config.json")
except json.JSONDecodeError as e:
    print(f"JSON parsing error: {e}")
except yaml.YAMLError as e:
    print(f"YAML parsing error: {e}")
```
