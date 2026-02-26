"""Order Manager for TradingAgents.

Manages order lifecycle and tracking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tradingagents.trading import Order, OrderStatus, TradingInterface

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages order lifecycle and tracking.
    
    Tracks orders from submission to completion.
    """
    
    def __init__(self, trading_interface: TradingInterface):
        """Initialize order manager.
        
        Args:
            trading_interface: TradingInterface instance
        """
        self.trading_interface = trading_interface
        self._orders: Dict[str, Order] = {}
        self._logger = logging.getLogger(__name__)
    
    def track_order(self, order: Order):
        """Track an order.
        
        Args:
            order: Order to track
        """
        if order.order_id:
            self._orders[order.order_id] = order
            self._logger.debug("Tracking order: %s", order.order_id)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order object or None
        """
        return self._orders.get(order_id)
    
    def update_order_status(self, order_id: str) -> Optional[Order]:
        """Update order status from trading interface.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Updated order or None
        """
        try:
            order = self.trading_interface.get_order_status(order_id)
            self._orders[order_id] = order
            return order
        except Exception as e:
            self._logger.exception("Failed to update order status %s: %s", order_id, e)
            return None
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders.
        
        Returns:
            List of pending orders
        """
        pending_statuses = [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        ]
        return [
            order for order in self._orders.values()
            if order.status in pending_statuses
        ]
    
    def get_filled_orders(self) -> List[Order]:
        """Get all filled orders.
        
        Returns:
            List of filled orders
        """
        return [
            order for order in self._orders.values()
            if order.status == OrderStatus.FILLED
        ]
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            True if cancellation successful, False otherwise
        """
        try:
            success = self.trading_interface.cancel_order(order_id)
            if success:
                # Update order status
                order = self.get_order(order_id)
                if order:
                    order.status = OrderStatus.CANCELLED
                    order.updated_at = datetime.now()
            return success
        except Exception as e:
            self._logger.exception("Failed to cancel order %s: %s", order_id, e)
            return False
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol.
        
        Args:
            symbol: Symbol to filter by
            
        Returns:
            List of orders for the symbol
        """
        return [
            order for order in self._orders.values()
            if order.symbol == symbol
        ]
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Get all orders with a specific status.
        
        Args:
            status: Order status to filter by
            
        Returns:
            List of orders with the status
        """
        return [
            order for order in self._orders.values()
            if order.status == status
        ]
    
    def list_all_orders(self) -> List[Order]:
        """List all tracked orders.
        
        Returns:
            List of all orders
        """
        return list(self._orders.values())
    
    def clear_completed_orders(self, days: int = 30):
        """Clear completed orders older than specified days.
        
        Args:
            days: Number of days to keep orders
        """
        cutoff_date = datetime.now().replace(day=datetime.now().day - days)
        to_remove = []
        
        for order_id, order in self._orders.items():
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.EXPIRED]:
                if order.updated_at and order.updated_at < cutoff_date:
                    to_remove.append(order_id)
        
        for order_id in to_remove:
            del self._orders[order_id]
        
        self._logger.info("Cleared %d completed orders older than %d days", len(to_remove), days)
