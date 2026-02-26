"""Decision Parser for TradingAgents.

Parses final_trade_decision using structured output for reliable parsing.
"""

import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TradeDecision(BaseModel):
    """Structured trade decision output."""
    action: str = Field(description="Trading action: BUY, SELL, or HOLD")
    quantity: Optional[float] = Field(default=None, description="Number of shares to trade (required for BUY/SELL)")
    order_type: str = Field(default="MARKET", description="Order type: MARKET, LIMIT, STOP, STOP_LIMIT")
    limit_price: Optional[float] = Field(default=None, description="Limit price (required for LIMIT orders)")
    stop_price: Optional[float] = Field(default=None, description="Stop price (required for STOP orders)")
    reason: Optional[str] = Field(default=None, description="Reason for the decision")


class DecisionParser:
    """Parser for trade decisions using structured output."""
    
    def __init__(self, llm):
        """Initialize decision parser.
        
        Args:
            llm: Language model instance with structured output support
        """
        self.llm = llm
        self._logger = logging.getLogger(__name__)
    
    def parse_decision(self, decision_text: str) -> Optional[TradeDecision]:
        """Parse trade decision from text using structured output.
        
        Args:
            decision_text: Raw decision text from final_trade_decision
            
        Returns:
            Parsed TradeDecision or None if parsing failed
        """
        try:
            # Use structured output if available
            if hasattr(self.llm, "with_structured_output"):
                structured_llm = self.llm.with_structured_output(TradeDecision)
                result = structured_llm.invoke(
                    f"Parse the following trading decision into structured format:\n\n{decision_text}"
                )
                return result
            else:
                # Fallback to manual parsing
                return self._parse_manually(decision_text)
        except Exception as e:
            self._logger.exception("Failed to parse decision with structured output: %s", e)
            # Fallback to manual parsing
            return self._parse_manually(decision_text)
    
    def _parse_manually(self, decision_text: str) -> Optional[TradeDecision]:
        """Manual parsing fallback using regex and heuristics.
        
        Args:
            decision_text: Raw decision text
            
        Returns:
            Parsed TradeDecision or None
        """
        import re
        
        decision_upper = decision_text.upper()
        
        # Determine action
        action = "HOLD"
        if "BUY" in decision_upper or "PURCHASE" in decision_upper:
            action = "BUY"
        elif "SELL" in decision_upper:
            action = "SELL"
        elif "HOLD" in decision_upper or "NO ACTION" in decision_upper or "WAIT" in decision_upper:
            action = "HOLD"
        
        if action == "HOLD":
            return TradeDecision(action="HOLD", reason=decision_text)
        
        # Extract quantity
        quantity = None
        qty_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:shares?|units?)',
            r'(\d+(?:\.\d+)?)\s*(?:shares?|units?)?',
            r'quantity[:\s]+(\d+(?:\.\d+)?)',
            r'qty[:\s]+(\d+(?:\.\d+)?)',
        ]
        for pattern in qty_patterns:
            match = re.search(pattern, decision_upper)
            if match:
                quantity = float(match.group(1))
                break
        
        # Extract order type
        order_type = "MARKET"
        if "LIMIT" in decision_upper:
            order_type = "LIMIT"
        elif "STOP" in decision_upper:
            if "LIMIT" in decision_upper:
                order_type = "STOP_LIMIT"
            else:
                order_type = "STOP"
        
        # Extract prices
        limit_price = None
        stop_price = None
        
        if order_type in ["LIMIT", "STOP_LIMIT"]:
            price_match = re.search(r'limit[:\s]+\$?(\d+(?:\.\d+)?)', decision_upper)
            if price_match:
                limit_price = float(price_match.group(1))
        
        if order_type in ["STOP", "STOP_LIMIT"]:
            stop_match = re.search(r'stop[:\s]+\$?(\d+(?:\.\d+)?)', decision_upper)
            if stop_match:
                stop_price = float(stop_match.group(1))
        
        return TradeDecision(
            action=action,
            quantity=quantity or 1.0,  # Default to 1 if not found
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            reason=decision_text,
        )
