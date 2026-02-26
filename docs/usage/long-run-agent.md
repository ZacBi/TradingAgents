# Long-Run Agent 使用指南

## 概述

Long-Run Agent功能使TradingAgents能够持续运行，支持状态恢复、定时调度、健康监控和指标收集。

## 快速开始

### 1. 基本配置

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.graph.long_run import LongRunAgent

# 配置PostgreSQL checkpoint
config = {
    "checkpoint_storage": "postgres",
    "checkpoint_postgres_url": "postgresql://user:password@localhost/tradingagents",
    "checkpointing_enabled": True,
}

# 创建graph
graph = TradingAgentsGraph(config=config)

# 创建Long-Run Agent
long_run_agent = LongRunAgent(graph)
```

### 2. 启动和调度

```python
# 启动Long-Run Agent
long_run_agent.start()

# 调度每日分析（市场开盘时）
long_run_agent.schedule_daily_analysis(
    company_name="AAPL",
    hour=9,
    minute=30,
    timezone="America/New_York"
)

# 调度间隔分析（每小时）
long_run_agent.schedule_interval_analysis(
    company_name="AAPL",
    minutes=60
)

# 检查健康状态
health = long_run_agent.get_health_status()
print(health)

# 列出所有调度任务
jobs = long_run_agent.list_scheduled_jobs()
for job in jobs:
    print(f"{job['id']}: {job['next_run_time']}")
```

### 3. 状态恢复

Long-Run Agent自动支持状态恢复。如果工作流中断，可以从checkpoint恢复：

```python
# 状态恢复是自动的
# 在propagate()方法中，如果发现checkpoint，会自动恢复状态
final_state, signal = graph.propagate("AAPL", "2025-02-26")
# 如果之前有未完成的运行，状态会自动恢复
```

### 4. 停止Agent

```python
# 停止Long-Run Agent（等待当前任务完成）
long_run_agent.stop(wait=True)
```

## 配置选项

### Checkpoint配置

```python
config = {
    # PostgreSQL checkpoint
    "checkpoint_storage": "postgres",
    "checkpoint_postgres_url": "postgresql://user:password@localhost/tradingagents",
    
    # 或使用SQLite（开发环境）
    # "checkpoint_storage": "sqlite",
    # "checkpoint_db_path": "checkpoints.db",
    
    # 或使用内存（不持久化）
    # "checkpoint_storage": "memory",
}
```

### 调度器配置

```python
# 在LongRunAgent初始化时配置
from tradingagents.scheduler import TradingAgentScheduler

scheduler = TradingAgentScheduler(timezone="America/New_York")
long_run_agent = LongRunAgent(graph, scheduler=scheduler)
```

### 监控配置

```python
from tradingagents.monitoring import HealthMonitor, MetricsCollector

# 自定义健康监控
health_monitor = HealthMonitor()

# 自定义指标收集（Prometheus）
metrics_collector = MetricsCollector(
    enable_prometheus=True,
    prometheus_port=8000
)

long_run_agent = LongRunAgent(
    graph,
    health_monitor=health_monitor,
    metrics_collector=metrics_collector,
)
```

## 高级用法

### 自定义调度任务

```python
from datetime import datetime

def custom_analysis():
    trade_date = datetime.now().strftime("%Y-%m-%d")
    final_state, signal = graph.propagate("AAPL", trade_date)
    print(f"Analysis result: {signal}")

# 使用Cron表达式
long_run_agent.scheduler.add_cron_job(
    job_id="custom_analysis",
    func=custom_analysis,
    cron_expression="0 9 * * 1-5",  # 工作日上午9点
)
```

### 健康检查

```python
# 获取健康状态
health = long_run_agent.get_health_status()

if health["status"] == "healthy":
    print("System is healthy")
elif health["status"] == "degraded":
    print("System is degraded, check details")
    for check_name, check_result in health["checks"].items():
        print(f"{check_name}: {check_result['status']}")
```

### Prometheus指标

Prometheus指标自动在端口8000（默认）上暴露：

```bash
# 访问指标端点
curl http://localhost:8000/metrics
```

主要指标：
- `tradingagents_agent_executions_total` - Agent执行总数
- `tradingagents_agent_execution_duration_seconds` - Agent执行时长
- `tradingagents_llm_calls_total` - LLM调用总数
- `tradingagents_trading_decisions_total` - 交易决策总数

## 故障恢复

### 自动恢复

Long-Run Agent支持自动状态恢复：

1. 如果工作流中断，下次运行时自动从checkpoint恢复
2. 状态合并：保留历史但允许继续执行
3. 错误恢复：自动重试失败的节点

### 手动恢复

```python
from tradingagents.graph.recovery import RecoveryEngine

# 获取恢复引擎
recovery_engine = graph.recovery_engine

# 检查是否可以恢复
thread_id = "AAPL-2025-02-26"
if recovery_engine.can_recover(thread_id):
    # 恢复状态
    recovered_state = recovery_engine.recover_state(thread_id)
    print("State recovered successfully")
```

## 最佳实践

1. **使用PostgreSQL checkpoint**：生产环境应使用PostgreSQL而非SQLite
2. **配置健康监控**：定期检查系统健康状态
3. **设置合理的重试次数**：避免无限重试
4. **监控Prometheus指标**：使用Grafana等工具可视化指标
5. **日志记录**：确保日志级别适当，便于调试

## 故障排查

### Checkpoint问题

```python
# 检查checkpoint状态
checkpoints = recovery_engine.list_checkpoints(thread_id)
print(f"Found {len(checkpoints)} checkpoints")
```

### 调度问题

```python
# 检查调度器状态
if long_run_agent.scheduler.is_running:
    jobs = long_run_agent.list_scheduled_jobs()
    for job in jobs:
        print(f"Job {job['id']}: next run at {job['next_run_time']}")
```

### 健康检查问题

```python
# 详细健康检查
health = long_run_agent.get_health_status()
for check_name, check_result in health["checks"].items():
    if check_result["status"] != "healthy":
        print(f"Check {check_name} failed: {check_result.get('error', 'Unknown error')}")
```
