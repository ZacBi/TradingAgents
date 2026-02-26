# 自主交易使用指南

## 概述

自主交易功能使TradingAgents能够根据分析结果自动执行交易订单，包括风险控制、订单管理和持仓跟踪。

## 快速开始

### 1. 基本配置

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph

# 配置交易功能
config = {
    "trading_enabled": True,
    "alpaca_api_key": "your_api_key",
    "alpaca_api_secret": "your_api_secret",
    "alpaca_paper": True,  # 使用paper trading
    "alpaca_base_url": "https://paper-api.alpaca.markets",
    
    # 风险控制配置
    "risk_config": {
        "max_position_size": 0.20,  # 最大仓位20%
        "max_portfolio_risk": 0.15,  # 最大组合风险15%
        "max_single_stock_exposure": 0.30,  # 单一股票最大暴露30%
        "stop_loss_pct": 0.05,  # 止损5%
        "take_profit_pct": 0.10,  # 止盈10%
    },
}

# 创建graph（交易功能会自动启用）
graph = TradingAgentsGraph(config=config)
```

### 2. 运行分析并执行交易

```python
# 运行分析
final_state, signal = graph.propagate("AAPL", "2025-02-26")

# 如果final_trade_decision是交易指令，会自动执行
# 例如："BUY 100 shares" 或 "SELL 50 shares" 或 "HOLD"

# 查看订单执行结果
if "order_execution_result" in final_state:
    result = final_state["order_execution_result"]
    if result["success"]:
        print(f"Order executed: {result['status']}")
        if result.get("order_id"):
            print(f"Order ID: {result['order_id']}")
    else:
        print(f"Order failed: {result.get('reason')}")
```

### 3. 手动管理订单和持仓

```python
# 获取订单管理器
order_manager = graph.order_manager

# 获取持仓管理器
position_manager = graph.position_manager

# 查看所有订单
all_orders = order_manager.list_all_orders()
pending_orders = order_manager.get_pending_orders()
filled_orders = order_manager.get_filled_orders()

# 查看持仓
positions = position_manager.get_all_positions()
portfolio_value = position_manager.get_portfolio_value()
total_pnl = position_manager.get_total_unrealized_pnl()

# 获取特定持仓
aapl_position = position_manager.get_position("AAPL")
if aapl_position:
    print(f"AAPL: {aapl_position.quantity} shares, P&L: ${aapl_position.unrealized_pnl:.2f}")
```

## 交易接口

### 支持的订单类型

```python
from tradingagents.trading import Order, OrderType

# Market订单
order = Order(
    symbol="AAPL",
    order_type=OrderType.MARKET,
    quantity=100,
    side="buy",
)

# Limit订单
order = Order(
    symbol="AAPL",
    order_type=OrderType.LIMIT,
    quantity=100,
    side="buy",
    limit_price=150.00,
)

# Stop订单
order = Order(
    symbol="AAPL",
    order_type=OrderType.STOP,
    quantity=100,
    side="sell",
    stop_price=140.00,
)

# Stop Limit订单
order = Order(
    symbol="AAPL",
    order_type=OrderType.STOP_LIMIT,
    quantity=100,
    side="sell",
    limit_price=139.50,
    stop_price=140.00,
)
```

### 手动提交订单

```python
from tradingagents.trading.order_executor import OrderExecutor

# 获取订单执行器
order_executor = graph.order_executor

# 执行订单
result = order_executor.execute_order(
    state=final_state,
    symbol="AAPL",
    side="buy",
    quantity=100,
    order_type=OrderType.MARKET,
)

if result["success"]:
    print(f"Order submitted: {result['order_id']}")
else:
    print(f"Order rejected: {result['reason']}")
```

## 风险控制

### 风险检查

```python
from tradingagents.trading.risk_controller import RiskController

risk_controller = graph.risk_controller

# 检查订单风险
order = Order(symbol="AAPL", order_type=OrderType.MARKET, quantity=100, side="buy")
is_allowed, reason = risk_controller.check_order_risk(
    order=order,
    current_positions=position_manager.get_all_positions(),
    account_info=graph.trading_interface.get_account_info(),
    portfolio_value=position_manager.get_portfolio_value(),
)

if not is_allowed:
    print(f"Order rejected: {reason}")
```

### 投资组合风险分析

```python
# 计算投资组合风险
risk_metrics = risk_controller.calculate_portfolio_risk(
    positions=position_manager.get_all_positions(),
    historical_prices=None,  # 可选：提供历史价格数据
)

print(f"Portfolio VaR (95%): {risk_metrics.get('var_95')}")
print(f"Portfolio CVaR (95%): {risk_metrics.get('cvar_95')}")
print(f"Portfolio Volatility: {risk_metrics.get('volatility')}")
```

### 投资组合优化

```python
# 优化投资组合
symbols = ["AAPL", "GOOGL", "MSFT"]
optimized = risk_controller.optimize_portfolio(
    symbols=symbols,
    expected_returns=None,  # 需要提供预期收益
    covariance=None,  # 需要提供协方差矩阵
    risk_measure="variance",
)

if "weights" in optimized:
    print("Optimized weights:")
    for symbol, weight in optimized["weights"].items():
        print(f"{symbol}: {weight:.2%}")
```

## 账户管理

### 获取账户信息

```python
# 获取账户信息
account_info = graph.trading_interface.get_account_info()

print(f"Cash: ${account_info['cash']:.2f}")
print(f"Portfolio Value: ${account_info['portfolio_value']:.2f}")
print(f"Buying Power: ${account_info['buying_power']:.2f}")
print(f"Equity: ${account_info['equity']:.2f}")
```

### 检查市场状态

```python
# 检查市场是否开放
if graph.trading_interface.is_market_open():
    print("Market is open")
else:
    print("Market is closed")
```

## 订单管理

### 查询订单状态

```python
# 获取订单状态
order = order_manager.get_order_status("order_id_123")
print(f"Order status: {order.status.value}")
print(f"Filled quantity: {order.filled_quantity}")
print(f"Average fill price: ${order.average_fill_price:.2f}")
```

### 取消订单

```python
# 取消订单
success = order_manager.cancel_order("order_id_123")
if success:
    print("Order cancelled successfully")
```

### 按条件查询订单

```python
# 按符号查询
aapl_orders = order_manager.get_orders_by_symbol("AAPL")

# 按状态查询
pending = order_manager.get_orders_by_status(OrderStatus.PENDING)
filled = order_manager.get_orders_by_status(OrderStatus.FILLED)
```

## 持仓管理

### 更新持仓价格

```python
# 刷新持仓并更新价格
position_manager.refresh_positions()
position_manager.update_position_prices()

# 获取持仓摘要
summary = position_manager.get_positions_summary()
print(f"Total positions: {summary['total_positions']}")
print(f"Portfolio value: ${summary['portfolio_value']:.2f}")
print(f"Total P&L: ${summary['total_unrealized_pnl']:.2f}")
```

### 计算P&L

```python
# 获取特定持仓的P&L
aapl_pnl = position_manager.get_position_pnl("AAPL")
if aapl_pnl:
    print(f"AAPL P&L: ${aapl_pnl:.2f}")

# 获取总P&L
total_pnl = position_manager.get_total_unrealized_pnl()
print(f"Total unrealized P&L: ${total_pnl:.2f}")
```

## 决策解析

OrderExecutor使用structured output解析交易决策。支持的格式：

- `"BUY 100 shares"` - 买入100股
- `"SELL 50 shares"` - 卖出50股
- `"HOLD"` - 持有，不操作
- `"BUY 100 shares LIMIT $150.00"` - 限价买入
- `"SELL 50 shares STOP $140.00"` - 止损卖出

## 配置选项

### 风险控制配置

```python
risk_config = {
    "max_position_size": 0.20,  # 最大仓位20%
    "max_portfolio_risk": 0.15,  # 最大组合风险15% (VaR)
    "max_single_stock_exposure": 0.30,  # 单一股票最大暴露30%
    "max_sector_exposure": 0.40,  # 单一行业最大暴露40%
    "stop_loss_pct": 0.05,  # 止损5%
    "take_profit_pct": 0.10,  # 止盈10%
    "max_daily_loss": 0.05,  # 最大日亏损5%
    "margin_requirement": 0.50,  # 做空/期权保证金要求50%
    "max_option_delta": 0.5,  # 期权最大delta
    "max_option_gamma": 0.1,  # 期权最大gamma
}
```

### Alpaca配置

```python
config = {
    "alpaca_api_key": "your_key",
    "alpaca_api_secret": "your_secret",
    "alpaca_paper": True,  # True for paper trading, False for live
    "alpaca_base_url": "https://paper-api.alpaca.markets",  # 可选，自动选择
}
```

## 最佳实践

1. **始终使用Paper Trading测试**：在生产环境前充分测试
2. **设置合理的风险限制**：根据资金规模设置仓位和风险限制
3. **监控订单状态**：定期检查订单执行状态
4. **跟踪持仓**：及时更新持仓价格，计算P&L
5. **错误处理**：处理订单拒绝和错误情况
6. **日志记录**：记录所有交易决策和执行结果

## 故障排查

### 订单被拒绝

```python
# 检查订单执行结果
result = final_state.get("order_execution_result", {})
if not result.get("success"):
    reason = result.get("reason")
    print(f"Order rejected: {reason}")
    
    # 常见原因：
    # - 风险控制限制
    # - 市场关闭
    # - 资金不足
    # - API错误
```

### 连接问题

```python
# 检查交易接口连接
if graph.trading_interface.is_connected:
    print("Connected to trading platform")
else:
    print("Not connected, attempting to connect...")
    graph.trading_interface.connect()
```

### 风险检查失败

```python
# 详细风险检查
is_allowed, reason = risk_controller.check_order_risk(...)
if not is_allowed:
    print(f"Risk check failed: {reason}")
    # 调整订单参数后重试
```
