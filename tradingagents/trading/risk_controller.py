"""Risk Controller for TradingAgents.

Provides risk management using skfolio for portfolio optimization and risk analysis.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import skfolio
try:
    import skfolio
    from skfolio import Portfolio, RiskMeasure
    from skfolio.optimization import MeanRisk
    from skfolio.preprocessing import prices_to_returns
    SKFOLIO_AVAILABLE = True
except ImportError:
    SKFOLIO_AVAILABLE = False
    logger.warning("skfolio not available. Install with: pip install skfolio")


class RiskController:
    """Risk controller for trading operations.
    
    Uses skfolio for portfolio optimization and risk management.
    Provides risk checks before order execution.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize risk controller.
        
        Args:
            config: Configuration dictionary with risk limits:
                - max_position_size: Maximum position size as % of portfolio
                - max_portfolio_risk: Maximum portfolio risk (VaR/CVaR)
                - max_single_stock_exposure: Maximum exposure to single stock
                - max_sector_exposure: Maximum exposure to single sector
                - stop_loss_pct: Stop loss percentage
                - take_profit_pct: Take profit percentage
                - max_daily_loss: Maximum daily loss
                - margin_requirement: Margin requirement for short/options
        """
        if not SKFOLIO_AVAILABLE:
            logger.warning("skfolio not available. RiskController will have limited functionality.")
        
        self.config = config
        self._logger = logging.getLogger(__name__)
        
        # Risk limits
        self.max_position_size = config.get("max_position_size", 0.20)  # 20% max
        self.max_portfolio_risk = config.get("max_portfolio_risk", 0.15)  # 15% VaR
        self.max_single_stock_exposure = config.get("max_single_stock_exposure", 0.30)  # 30%
        self.max_sector_exposure = config.get("max_sector_exposure", 0.40)  # 40%
        self.stop_loss_pct = config.get("stop_loss_pct", 0.05)  # 5% stop loss
        self.take_profit_pct = config.get("take_profit_pct", 0.10)  # 10% take profit
        self.max_daily_loss = config.get("max_daily_loss", 0.05)  # 5% max daily loss
        self.margin_requirement = config.get("margin_requirement", 0.50)  # 50% margin for short/options
    
    def check_order_risk(
        self,
        order: Any,  # Order from trading.interface
        current_positions: List[Any],  # List of Position objects
        account_info: Dict[str, Any],
        portfolio_value: float,
    ) -> tuple[bool, Optional[str]]:
        """Check if an order passes risk controls.
        
        Args:
            order: Order to check
            current_positions: Current positions
            account_info: Account information
            portfolio_value: Current portfolio value
            
        Returns:
            Tuple of (is_allowed, reason_if_rejected)
        """
        # Check 1: Position size limit
        order_value = self._calculate_order_value(order, portfolio_value)
        position_size_pct = order_value / portfolio_value if portfolio_value > 0 else 0
        
        if position_size_pct > self.max_position_size:
            return False, f"Order size ({position_size_pct:.2%}) exceeds max position size ({self.max_position_size:.2%})"
        
        # Check 2: Single stock exposure limit
        current_position = self._get_position_for_symbol(order.symbol, current_positions)
        if current_position:
            current_exposure = abs(current_position.quantity * (current_position.current_price or current_position.average_cost)) / portfolio_value
            new_exposure = abs(order.quantity * (order.limit_price or 0)) / portfolio_value if order.limit_price else position_size_pct
            
            if order.side == "buy":
                total_exposure = current_exposure + new_exposure
            else:  # sell
                total_exposure = max(0, current_exposure - new_exposure)
            
            if total_exposure > self.max_single_stock_exposure:
                return False, f"Total exposure to {order.symbol} ({total_exposure:.2%}) exceeds limit ({self.max_single_stock_exposure:.2%})"
        
        # Check 3: Buying power / margin check
        if order.side == "buy":
            if order_value > account_info.get("buying_power", 0):
                return False, f"Insufficient buying power. Required: ${order_value:.2f}, Available: ${account_info.get('buying_power', 0):.2f}"
        elif order.side == "sell" and order.order_type.value in ["short", "sell_call", "sell_put"]:
            # Short selling or option selling requires margin
            margin_required = order_value * self.margin_requirement
            if margin_required > account_info.get("buying_power", 0):
                return False, f"Insufficient margin. Required: ${margin_required:.2f}, Available: ${account_info.get('buying_power', 0):.2f}"
        
        # Check 4: Options-specific risk (Greeks)
        if order.order_type.value in ["buy_call", "sell_call", "buy_put", "sell_put"]:
            # For options, check Greeks if available
            # This is a simplified check - real implementation would calculate Greeks
            if order.order_type.value in ["sell_call", "sell_put"]:
                # Selling options requires more margin
                margin_required = order_value * 1.5  # Higher margin for naked options
                if margin_required > account_info.get("buying_power", 0):
                    return False, f"Insufficient margin for option selling. Required: ${margin_required:.2f}"
        
        # Check 5: Daily loss limit (simplified - would need to track daily P&L)
        # This would require tracking daily P&L, which is not implemented here
        
        # All checks passed
        return True, None
    
    def calculate_portfolio_risk(
        self,
        positions: List[Any],
        historical_prices: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Calculate portfolio risk metrics using skfolio.
        
        Args:
            positions: List of Position objects
            historical_prices: Optional historical price data (pandas DataFrame)
            
        Returns:
            Dictionary with risk metrics
        """
        if not SKFOLIO_AVAILABLE:
            return {"error": "skfolio not available"}
        
        if not positions:
            return {
                "portfolio_value": 0.0,
                "var_95": 0.0,
                "cvar_95": 0.0,
                "volatility": 0.0,
            }
        
        try:
            # Calculate portfolio value
            portfolio_value = sum(
                pos.quantity * (pos.current_price or pos.average_cost)
                for pos in positions
            )
            
            # If historical prices available, use skfolio for risk calculation
            if historical_prices is not None:
                # Convert prices to returns
                returns = prices_to_returns(historical_prices)
                
                # Create portfolio weights
                weights = {}
                for pos in positions:
                    symbol = pos.symbol
                    value = pos.quantity * (pos.current_price or pos.average_cost)
                    weights[symbol] = value / portfolio_value if portfolio_value > 0 else 0
                
                # Create portfolio
                portfolio = Portfolio(weights=weights)
                
                # Calculate risk measures
                var_95 = portfolio.risk_measure(RiskMeasure.VAR, confidence_level=0.95)
                cvar_95 = portfolio.risk_measure(RiskMeasure.CVAR, confidence_level=0.95)
                volatility = portfolio.risk_measure(RiskMeasure.VOLATILITY)
                
                return {
                    "portfolio_value": portfolio_value,
                    "var_95": var_95,
                    "cvar_95": cvar_95,
                    "volatility": volatility,
                    "weights": weights,
                }
            else:
                # Simplified risk calculation without historical data
                return {
                    "portfolio_value": portfolio_value,
                    "var_95": None,
                    "cvar_95": None,
                    "volatility": None,
                    "note": "Historical prices not provided for detailed risk calculation",
                }
        except Exception as e:
            self._logger.exception("Failed to calculate portfolio risk: %s", e)
            return {"error": str(e)}
    
    def optimize_portfolio(
        self,
        symbols: List[str],
        expected_returns: Optional[Any] = None,
        covariance: Optional[Any] = None,
        risk_measure: str = "variance",
    ) -> Dict[str, Any]:
        """Optimize portfolio allocation using skfolio.
        
        Args:
            symbols: List of symbols to optimize
            expected_returns: Expected returns (pandas Series or array)
            covariance: Covariance matrix (pandas DataFrame or array)
            risk_measure: Risk measure to optimize ("variance", "cvar", "evar")
            
        Returns:
            Dictionary with optimized weights
        """
        if not SKFOLIO_AVAILABLE:
            return {"error": "skfolio not available"}
        
        try:
            # Create MeanRisk optimizer
            if risk_measure == "variance":
                optimizer = MeanRisk(risk_measure=RiskMeasure.VARIANCE)
            elif risk_measure == "cvar":
                optimizer = MeanRisk(risk_measure=RiskMeasure.CVAR)
            elif risk_measure == "evar":
                optimizer = MeanRisk(risk_measure=RiskMeasure.EVAR)
            else:
                optimizer = MeanRisk(risk_measure=RiskMeasure.VARIANCE)
            
            # Fit optimizer
            if expected_returns is not None and covariance is not None:
                portfolio = optimizer.fit(expected_returns, covariance)
                weights = portfolio.weights_
                
                return {
                    "weights": dict(zip(symbols, weights)),
                    "expected_return": portfolio.expected_return_,
                    "risk": portfolio.risk_,
                }
            else:
                return {"error": "Expected returns and covariance required"}
        except Exception as e:
            self._logger.exception("Failed to optimize portfolio: %s", e)
            return {"error": str(e)}
    
    def _calculate_order_value(self, order: Any, portfolio_value: float) -> float:
        """Calculate order value.
        
        Args:
            order: Order object
            portfolio_value: Portfolio value for percentage-based calculations
            
        Returns:
            Order value in dollars
        """
        # Use limit price if available, otherwise estimate from portfolio value
        price = order.limit_price or (portfolio_value * 0.01)  # Fallback estimate
        return order.quantity * price
    
    def _get_position_for_symbol(self, symbol: str, positions: List[Any]) -> Optional[Any]:
        """Get position for a symbol.
        
        Args:
            symbol: Symbol to find
            positions: List of positions
            
        Returns:
            Position object or None
        """
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None
