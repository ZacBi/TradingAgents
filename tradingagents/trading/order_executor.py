"""Order Executor Node for TradingAgents.

Executes trading orders through TradingInterface with risk controls.
"""

import logging
from typing import Any, Dict, Optional

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.trading import Order, OrderType, TradingInterface
from tradingagents.trading.decision_parser import DecisionParser, TradeDecision
from tradingagents.trading.risk_controller import RiskController

logger = logging.getLogger(__name__)


class OrderExecutor:
    """Order executor for TradingAgents workflow.
    
    Executes orders through TradingInterface after risk checks.
    """
    
    def __init__(
        self,
        trading_interface: TradingInterface,
        risk_controller: RiskController,
        llm=None,
    ):
        """Initialize order executor.
        
        Args:
            trading_interface: TradingInterface instance
            risk_controller: RiskController instance
            llm: Optional LLM for structured output parsing
        """
        self.trading_interface = trading_interface
        self.risk_controller = risk_controller
        self.decision_parser = DecisionParser(llm) if llm else None
        self._logger = logging.getLogger(__name__)
    
    def execute_order(
        self,
        state: AgentState,
        symbol: str,
        side: str,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute a trading order.
        
        Args:
            state: Current agent state
            symbol: Symbol to trade
            side: "buy" or "sell"
            quantity: Order quantity
            order_type: Order type
            limit_price: Optional limit price
            stop_price: Optional stop price
            
        Returns:
            Dictionary with execution result
        """
        # Create order
        order = Order(
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            side=side,
            limit_price=limit_price,
            stop_price=stop_price,
        )
        
        # Get account info and positions for risk check
        try:
            account_info = self.trading_interface.get_account_info()
            positions = self.trading_interface.get_positions()
            portfolio_value = account_info.get("portfolio_value", 0.0)
            
            # Risk check
            is_allowed, reason = self.risk_controller.check_order_risk(
                order=order,
                current_positions=positions,
                account_info=account_info,
                portfolio_value=portfolio_value,
            )
            
            if not is_allowed:
                self._logger.warning("Order rejected by risk controller: %s", reason)
                return {
                    "success": False,
                    "order": order,
                    "reason": reason,
                    "status": "rejected",
                }
            
            # Check if market is open
            if not self.trading_interface.is_market_open():
                self._logger.warning("Market is closed, order will be queued")
                # In a real implementation, orders could be queued
                return {
                    "success": False,
                    "order": order,
                    "reason": "Market is closed",
                    "status": "pending",
                }
            
            # Submit order
            try:
                submitted_order = self.trading_interface.submit_order(order)
                
                if submitted_order.status.value in ["filled", "partially_filled"]:
                    self._logger.info("Order executed: %s %s %s @ %s", side, quantity, symbol, submitted_order.average_fill_price)
                    return {
                        "success": True,
                        "order": submitted_order,
                        "status": submitted_order.status.value,
                        "filled_quantity": submitted_order.filled_quantity,
                        "average_fill_price": submitted_order.average_fill_price,
                    }
                else:
                    self._logger.info("Order submitted: %s (status: %s)", submitted_order.order_id, submitted_order.status.value)
                    return {
                        "success": True,
                        "order": submitted_order,
                        "status": submitted_order.status.value,
                        "order_id": submitted_order.order_id,
                    }
            except Exception as e:
                self._logger.exception("Failed to submit order: %s", e)
                return {
                    "success": False,
                    "order": order,
                    "reason": str(e),
                    "status": "error",
                }
        except Exception as e:
            self._logger.exception("Order execution failed: %s", e)
            return {
                "success": False,
                "order": order,
                "reason": str(e),
                "status": "error",
            }
    
    def create_order_executor_node(self):
        """Create a LangGraph node function for order execution.
        
        Returns:
            Node function that can be added to the graph
        """
        def order_executor_node(state: AgentState) -> Dict[str, Any]:
            """Execute orders based on final trade decision.
            
            Args:
                state: Current agent state
                
            Returns:
                State update with order execution results
            """
            final_decision = state.get("final_trade_decision", "")
            company_of_interest = state.get("company_of_interest", "")
            
            # Parse decision using structured output or fallback parser
            if self.decision_parser:
                trade_decision = self.decision_parser.parse_decision(final_decision)
            else:
                # Fallback: create parser without LLM (uses manual parsing)
                from tradingagents.trading.decision_parser import DecisionParser
                parser = DecisionParser(None)
                trade_decision = parser._parse_manually(final_decision)
            
            if not trade_decision:
                return {
                    "order_execution_result": {
                        "success": False,
                        "reason": "Failed to parse decision",
                        "decision": final_decision,
                    }
                }
            
            # Handle HOLD action
            if trade_decision.action == "HOLD":
                return {
                    "order_execution_result": {
                        "success": True,
                        "action": "hold",
                        "message": "No action taken",
                        "reason": trade_decision.reason,
                    }
                }
            
            # Map order type
            order_type_map = {
                "MARKET": OrderType.MARKET,
                "LIMIT": OrderType.LIMIT,
                "STOP": OrderType.STOP,
                "STOP_LIMIT": OrderType.STOP_LIMIT,
            }
            order_type = order_type_map.get(trade_decision.order_type, OrderType.MARKET)
            
            # Execute order
            if trade_decision.quantity:
                result = self.execute_order(
                    state=state,
                    symbol=company_of_interest,
                    side=trade_decision.action.lower(),
                    quantity=trade_decision.quantity,
                    order_type=order_type,
                    limit_price=trade_decision.limit_price,
                    stop_price=trade_decision.stop_price,
                )
                
                return {
                    "order_execution_result": result,
                }
            else:
                return {
                    "order_execution_result": {
                        "success": False,
                        "reason": "No quantity specified in decision",
                        "decision": final_decision,
                    }
                }
        
        return order_executor_node
