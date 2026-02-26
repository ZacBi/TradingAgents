"""Position Manager for TradingAgents.

Manages position tracking and updates.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tradingagents.trading import Position, TradingInterface

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages position tracking and updates.
    
    Tracks positions and provides real-time updates.
    """
    
    def __init__(self, trading_interface: TradingInterface):
        """Initialize position manager.
        
        Args:
            trading_interface: TradingInterface instance
        """
        self.trading_interface = trading_interface
        self._positions: Dict[str, Position] = {}
        self._logger = logging.getLogger(__name__)
    
    def refresh_positions(self) -> List[Position]:
        """Refresh positions from trading interface.
        
        Returns:
            List of current positions
        """
        try:
            positions = self.trading_interface.get_positions()
            
            # Update internal cache
            for pos in positions:
                self._positions[pos.symbol] = pos
            
            # Remove positions that no longer exist
            current_symbols = {pos.symbol for pos in positions}
            to_remove = [sym for sym in self._positions.keys() if sym not in current_symbols]
            for sym in to_remove:
                del self._positions[sym]
            
            self._logger.debug("Refreshed %d positions", len(positions))
            return positions
        except Exception as e:
            self._logger.exception("Failed to refresh positions: %s", e)
            return []
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol.
        
        Args:
            symbol: Symbol to get position for
            
        Returns:
            Position object or None
        """
        # Try to get from cache first
        if symbol in self._positions:
            return self._positions[symbol]
        
        # Try to get from trading interface
        try:
            position = self.trading_interface.get_position(symbol)
            if position:
                self._positions[symbol] = position
            return position
        except Exception as e:
            self._logger.exception("Failed to get position for %s: %s", symbol, e)
            return None
    
    def get_all_positions(self) -> List[Position]:
        """Get all current positions.
        
        Returns:
            List of all positions
        """
        return list(self._positions.values())
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value.
        
        Returns:
            Total portfolio value
        """
        return sum(
            pos.market_value or (pos.quantity * pos.average_cost)
            for pos in self._positions.values()
        )
    
    def get_total_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L.
        
        Returns:
            Total unrealized P&L
        """
        return sum(
            pos.unrealized_pnl or 0.0
            for pos in self._positions.values()
        )
    
    def get_position_pnl(self, symbol: str) -> Optional[float]:
        """Get P&L for a specific position.
        
        Args:
            symbol: Symbol to get P&L for
            
        Returns:
            Unrealized P&L or None
        """
        position = self.get_position(symbol)
        if position:
            return position.unrealized_pnl
        return None
    
    def update_position_prices(self):
        """Update position prices from market data.
        
        Updates current_price and market_value for all positions.
        """
        for symbol, position in self._positions.items():
            try:
                current_price = self.trading_interface.get_market_price(symbol)
                if current_price:
                    position.current_price = current_price
                    position.market_value = position.quantity * current_price
                    
                    # Calculate unrealized P&L
                    if position.average_cost:
                        position.unrealized_pnl = (current_price - position.average_cost) * position.quantity
                    
                    position.updated_at = datetime.now()
            except Exception as e:
                self._logger.exception("Failed to update price for %s: %s", symbol, e)
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Get summary of all positions.
        
        Returns:
            Dictionary with position summary
        """
        self.refresh_positions()
        self.update_position_prices()
        
        return {
            "total_positions": len(self._positions),
            "portfolio_value": self.get_portfolio_value(),
            "total_unrealized_pnl": self.get_total_unrealized_pnl(),
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "average_cost": pos.average_cost,
                    "current_price": pos.current_price,
                    "market_value": pos.market_value,
                    "unrealized_pnl": pos.unrealized_pnl,
                }
                for pos in self._positions.values()
            ],
        }
