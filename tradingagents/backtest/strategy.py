"""Backtrader strategy that executes trades based on agent decisions.

Decision on date D is executed at the open of the next bar (D+1).
"""


import backtrader as bt


class AgentDecisionStrategy(bt.Strategy):
    """Execute BUY/SELL at next bar open based on agent decision map.

    params:
        decisions: dict mapping trade_date (YYYY-MM-DD) -> "BUY" | "SELL" | "HOLD"
        allocation: fraction of cash to use per trade (0.0-1.0), default 1.0
    """

    params = (
        ("decisions", {}),
        ("allocation", 1.0),
    )

    def __init__(self) -> None:
        self._prev_bar_date: str | None = None
        self._order = None

    def next(self) -> None:
        # Current bar date (we will execute the decision that was made for prev bar)
        try:
            current_dt = self.datas[0].datetime.datetime(0)
            current_date = current_dt.strftime("%Y-%m-%d")
        except Exception:
            return

        decisions: dict[str, str] = self.p.decisions
        decision = (decisions or {}).get(self._prev_bar_date, "HOLD")
        decision = (decision or "").strip().upper()
        if decision not in ("BUY", "SELL", "HOLD"):
            decision = "HOLD"

        # Execute previous bar's decision at this bar's open
        if decision == "BUY" and not self.position:
            size = self.broker.getcash() * self.p.allocation / self.datas[0].open[0]
            if size > 0:
                self._order = self.buy(size=size, exectype=bt.Order.Market)
        elif decision == "SELL" and self.position:
            self._order = self.close(exectype=bt.Order.Market)

        self._prev_bar_date = current_date

    def notify_order(self, order: bt.Order) -> None:
        if order.status in (order.Completed, order.Canceled, order.Margin):
            self._order = None
