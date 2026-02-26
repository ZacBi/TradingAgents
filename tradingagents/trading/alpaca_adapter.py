"""Alpaca Trading Adapter for TradingAgents.

Implements TradingInterface for Alpaca Markets API.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tradingagents.trading.interface import (
    Order,
    OrderStatus,
    OrderType,
    Position,
    TradingInterface,
)

logger = logging.getLogger(__name__)

# Try to import Alpaca SDK
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus as AlpacaOrderStatus
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logger.warning("alpaca-py not available. Install with: pip install alpaca-py")


class AlpacaAdapter(TradingInterface):
    """Alpaca Markets trading adapter.
    
    Implements TradingInterface using Alpaca API.
    Supports paper trading and live trading.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Alpaca adapter.
        
        Args:
            config: Configuration dictionary with:
                - api_key: Alpaca API key
                - api_secret: Alpaca API secret
                - base_url: API base URL (default: paper trading URL)
                - paper: Whether to use paper trading (default: True)
        """
        if not ALPACA_AVAILABLE:
            raise ImportError("alpaca-py is required. Install with: pip install alpaca-py")
        
        super().__init__(config)
        self.api_key = config.get("api_key") or config.get("alpaca_api_key")
        self.api_secret = config.get("api_secret") or config.get("alpaca_api_secret")
        self.paper = config.get("paper", True)
        
        # Set base URL based on paper/live
        if self.paper:
            self.base_url = config.get("base_url", "https://paper-api.alpaca.markets")
        else:
            self.base_url = config.get("base_url", "https://api.alpaca.markets")
        
        self.client: Optional[TradingClient] = None
        self._data_client = None  # Cached data client for market data
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to Alpaca API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                paper=self.paper,
            )
            
            # Test connection by getting account info
            account = self.client.get_account()
            self._connected = True
            self._logger.info("Connected to Alpaca API (paper=%s)", self.paper)
            return True
        except Exception as e:
            self._logger.exception("Failed to connect to Alpaca API: %s", e)
            self._connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Alpaca API."""
        self.client = None
        self._data_client = None
        self._connected = False
        self._logger.info("Disconnected from Alpaca API")
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information.
        
        Returns:
            Dictionary with account details
        """
        if not self._connected:
            raise RuntimeError("Not connected to Alpaca API")
        
        account = self.client.get_account()
        return {
            "account_number": account.account_number,
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "pattern_day_trader": account.pattern_day_trader,
            "trading_blocked": account.trading_blocked,
            "account_blocked": account.account_blocked,
        }
    
    def submit_order(self, order: Order) -> Order:
        """Submit a trading order.
        
        Args:
            order: Order to submit
            
        Returns:
            Order with order_id and status updated
        """
        if not self._connected:
            raise RuntimeError("Not connected to Alpaca API")
        
        # Validate order
        is_valid, error_msg = self.validate_order(order)
        if not is_valid:
            order.status = OrderStatus.REJECTED
            order.notes = error_msg
            return order
        
        try:
            # Convert OrderType to Alpaca order request
            side = OrderSide.BUY if order.side == "buy" else OrderSide.SELL
            
            # Map time_in_force
            tif_map = {
                "day": TimeInForce.DAY,
                "gtc": TimeInForce.GTC,
                "ioc": TimeInForce.IOC,
                "fok": TimeInForce.FOK,
            }
            time_in_force = tif_map.get(order.time_in_force.lower(), TimeInForce.DAY)
            
            # Create appropriate order request based on order type
            if order.order_type == OrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    time_in_force=time_in_force,
                )
            elif order.order_type == OrderType.LIMIT:
                order_request = LimitOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    limit_price=order.limit_price,
                    time_in_force=time_in_force,
                )
            elif order.order_type == OrderType.STOP:
                order_request = StopOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    stop_price=order.stop_price,
                    time_in_force=time_in_force,
                )
            elif order.order_type == OrderType.STOP_LIMIT:
                order_request = StopLimitOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    limit_price=order.limit_price,
                    stop_price=order.stop_price,
                    time_in_force=time_in_force,
                )
            else:
                # For now, only support basic order types
                # Options and multi-leg strategies require additional implementation
                order.status = OrderStatus.REJECTED
                order.notes = f"Order type {order.order_type} not yet implemented for Alpaca"
                return order
            
            # Submit order
            alpaca_order = self.client.submit_order(order_data=order_request)
            
            # Update order with response
            order.order_id = str(alpaca_order.id)
            order.status = self._map_alpaca_status(alpaca_order.status)
            order.created_at = datetime.now()
            
            self._logger.info("Order submitted: %s", order.order_id)
            return order
            
        except Exception as e:
            self._logger.exception("Failed to submit order: %s", e)
            order.status = OrderStatus.REJECTED
            order.notes = str(e)
            return order
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            True if cancellation successful, False otherwise
        """
        if not self._connected:
            raise RuntimeError("Not connected to Alpaca API")
        
        try:
            self.client.cancel_order_by_id(order_id)
            self._logger.info("Order cancelled: %s", order_id)
            return True
        except Exception as e:
            self._logger.exception("Failed to cancel order %s: %s", order_id, e)
            return False
    
    def get_order_status(self, order_id: str) -> Order:
        """Get order status.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order with current status
        """
        if not self._connected:
            raise RuntimeError("Not connected to Alpaca API")
        
        try:
            alpaca_order = self.client.get_order_by_id(order_id)
            
            # Convert to Order object
            order = Order(
                symbol=alpaca_order.symbol,
                order_type=self._map_alpaca_order_type(alpaca_order),
                quantity=float(alpaca_order.qty),
                side="buy" if alpaca_order.side == OrderSide.BUY else "sell",
                limit_price=float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
                stop_price=float(alpaca_order.stop_price) if alpaca_order.stop_price else None,
                order_id=str(alpaca_order.id),
                status=self._map_alpaca_status(alpaca_order.status),
                filled_quantity=float(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0.0,
                average_fill_price=float(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None,
            )
            return order
        except Exception as e:
            self._logger.exception("Failed to get order status %s: %s", order_id, e)
            raise
    
    def get_positions(self) -> List[Position]:
        """Get all current positions.
        
        Returns:
            List of Position objects
        """
        if not self._connected:
            raise RuntimeError("Not connected to Alpaca API")
        
        try:
            alpaca_positions = self.client.get_all_positions()
            positions = []
            
            for ap in alpaca_positions:
                position = Position(
                    symbol=ap.symbol,
                    quantity=float(ap.qty),
                    average_cost=float(ap.avg_entry_price),
                    current_price=float(ap.current_price) if ap.current_price else None,
                    market_value=float(ap.market_value) if ap.market_value else None,
                    unrealized_pnl=float(ap.unrealized_pl) if ap.unrealized_pl else None,
                    updated_at=datetime.now(),
                )
                positions.append(position)
            
            return positions
        except Exception as e:
            self._logger.exception("Failed to get positions: %s", e)
            return []
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol.
        
        Args:
            symbol: Symbol to get position for
            
        Returns:
            Position object or None if not found
        """
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None
    
    def get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol.
        
        Args:
            symbol: Symbol to get price for
            
        Returns:
            Current market price or None if unavailable
        """
        if not self._connected:
            raise RuntimeError("Not connected to Alpaca API")
        
        try:
            # Use cached data client or create one
            if self._data_client is None:
                from alpaca.data.historical import StockHistoricalDataClient
                self._data_client = StockHistoricalDataClient(
                    api_key=self.api_key,
                    secret_key=self.api_secret,
                )
            
            from alpaca.data.requests import StockLatestQuoteRequest
            
            request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
            quote = self._data_client.get_stock_latest_quote(request)
            
            if quote and symbol in quote:
                # Return mid price
                bid = quote[symbol].bid_price
                ask = quote[symbol].ask_price
                if bid and ask:
                    return (bid + ask) / 2.0
                elif bid:
                    return bid
                elif ask:
                    return ask
            
            return None
        except Exception as e:
            self._logger.exception("Failed to get market price for %s: %s", symbol, e)
            return None
    
    def is_market_open(self) -> bool:
        """Check if market is currently open.
        
        Returns:
            True if market is open, False otherwise
        """
        if not self._connected:
            return False
        
        try:
            clock = self.client.get_clock()
            return clock.is_open
        except Exception as e:
            self._logger.exception("Failed to check market status: %s", e)
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Alpaca API."""
        return self._connected
    
    def _map_alpaca_status(self, alpaca_status: Any) -> OrderStatus:
        """Map Alpaca order status to OrderStatus enum."""
        status_map = {
            AlpacaOrderStatus.NEW: OrderStatus.PENDING,
            AlpacaOrderStatus.ACCEPTED: OrderStatus.SUBMITTED,
            AlpacaOrderStatus.PENDING_NEW: OrderStatus.PENDING,
            AlpacaOrderStatus.PARTIALLY_FILLED: OrderStatus.PARTIALLY_FILLED,
            AlpacaOrderStatus.FILLED: OrderStatus.FILLED,
            AlpacaOrderStatus.DONE_FOR_DAY: OrderStatus.CANCELLED,
            AlpacaOrderStatus.CANCELED: OrderStatus.CANCELLED,
            AlpacaOrderStatus.EXPIRED: OrderStatus.EXPIRED,
            AlpacaOrderStatus.REPLACED: OrderStatus.SUBMITTED,
            AlpacaOrderStatus.PENDING_CANCEL: OrderStatus.CANCELLED,
            AlpacaOrderStatus.PENDING_REPLACE: OrderStatus.SUBMITTED,
            AlpacaOrderStatus.REJECTED: OrderStatus.REJECTED,
        }
        return status_map.get(alpaca_status, OrderStatus.PENDING)
    
    def _map_alpaca_order_type(self, alpaca_order: Any) -> OrderType:
        """Map Alpaca order to OrderType enum."""
        # Simplified mapping - Alpaca orders have order_type field
        if hasattr(alpaca_order, "order_type"):
            order_type_str = str(alpaca_order.order_type).lower()
            if "market" in order_type_str:
                return OrderType.MARKET
            elif "limit" in order_type_str:
                if "stop" in order_type_str:
                    return OrderType.STOP_LIMIT
                return OrderType.LIMIT
            elif "stop" in order_type_str:
                return OrderType.STOP
        
        # Default to market
        return OrderType.MARKET
