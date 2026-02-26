"""Trading Interface Abstraction for TradingAgents.

Provides a unified interface for different trading platforms (Alpaca, IB, etc.).
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types supported by trading interface."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    # Options
    BUY_CALL = "buy_call"
    SELL_CALL = "sell_call"
    BUY_PUT = "buy_put"
    SELL_PUT = "sell_put"
    # Multi-leg strategies
    COVERED_CALL = "covered_call"
    PROTECTIVE_PUT = "protective_put"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    IRON_CONDOR = "iron_condor"
    BUTTERFLY = "butterfly"
    # Short selling
    SHORT = "short"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Order:
    """Represents a trading order."""
    symbol: str
    order_type: OrderType
    quantity: float
    side: str  # "buy" or "sell"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"  # "day", "gtc", "ioc", "fok"
    # Options-specific fields
    option_symbol: Optional[str] = None
    strike_price: Optional[float] = None
    expiration_date: Optional[datetime] = None
    option_type: Optional[str] = None  # "call" or "put"
    # Multi-leg strategy fields
    legs: Optional[List[Dict[str, Any]]] = None
    # Metadata
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    quantity: float
    average_cost: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None
    # Options-specific
    option_symbol: Optional[str] = None
    strike_price: Optional[float] = None
    expiration_date: Optional[datetime] = None
    # Greeks (for options)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    # Metadata
    updated_at: Optional[datetime] = None


class TradingInterface(ABC):
    """Abstract interface for trading operations.
    
    Provides a unified API for different trading platforms.
    Subclasses must implement platform-specific logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize trading interface.
        
        Args:
            config: Configuration dictionary with API keys, endpoints, etc.
        """
        self.config = config
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to trading platform.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from trading platform."""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information.
        
        Returns:
            Dictionary with account details (balance, buying power, etc.)
        """
        pass
    
    @abstractmethod
    def submit_order(self, order: Order) -> Order:
        """Submit a trading order.
        
        Args:
            order: Order to submit
            
        Returns:
            Order with order_id and status updated
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            True if cancellation successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Order:
        """Get order status.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order with current status
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all current positions.
        
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol.
        
        Args:
            symbol: Symbol to get position for
            
        Returns:
            Position object or None if not found
        """
        pass
    
    @abstractmethod
    def get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol.
        
        Args:
            symbol: Symbol to get price for
            
        Returns:
            Current market price or None if unavailable
        """
        pass
    
    def validate_order(self, order: Order) -> tuple[bool, Optional[str]]:
        """Validate order before submission.
        
        Args:
            order: Order to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if order.quantity <= 0:
            return False, "Quantity must be positive"
        
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if order.limit_price is None or order.limit_price <= 0:
                return False, "Limit price required for limit orders"
        
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if order.stop_price is None or order.stop_price <= 0:
                return False, "Stop price required for stop orders"
        
        return True, None
    
    def is_market_open(self) -> bool:
        """Check if market is currently open.
        
        Returns:
            True if market is open, False otherwise
        """
        # Default implementation - subclasses should override
        from datetime import datetime
        now = datetime.now()
        # Simple check: 9:30 AM - 4:00 PM ET on weekdays
        # This is a simplified check - real implementation should use market calendar
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        return True  # Simplified - should check actual market hours
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to trading platform."""
        pass
