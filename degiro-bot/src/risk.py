from dataclasses import dataclass

from .config import RiskConfig


@dataclass
class OrderPlan:
    approved: bool
    quantity: int
    reason: str


class DailyLossCircuitBreaker:
    """Tracks realized+unrealized P&L since the bot started today and halts
    all new orders once losses exceed the configured fraction of portfolio value."""

    def __init__(self, risk: RiskConfig):
        self.risk = risk
        self.starting_equity: float | None = None
        self.tripped = False

    def update(self, current_equity: float) -> None:
        if self.starting_equity is None:
            self.starting_equity = current_equity
            return
        drawdown = (self.starting_equity - current_equity) / self.starting_equity
        if drawdown >= self.risk.max_daily_loss_pct:
            self.tripped = True

    def reset_for_new_day(self, current_equity: float) -> None:
        self.starting_equity = current_equity
        self.tripped = False


def size_order(*, side: str, price: float, portfolio_value: float,
                cash_available: float, current_position_value: float,
                risk: RiskConfig, circuit_breaker: DailyLossCircuitBreaker,
                held_quantity: int = 0) -> OrderPlan:
    if price <= 0:
        return OrderPlan(False, 0, "invalid price")

    if side == "BUY":
        # The circuit breaker only blocks *new* risk. It must never block a
        # SELL: refusing to exit a losing position during a bad day would
        # turn a daily loss limit into a reason to hold through further losses.
        if circuit_breaker.tripped:
            return OrderPlan(False, 0, "daily loss circuit breaker tripped; no new orders today")

        max_position_value = portfolio_value * risk.max_position_pct
        room_left = max(max_position_value - current_position_value, 0)
        budget = min(room_left, cash_available, risk.max_order_value)
        quantity = int(budget // price)
        if quantity <= 0:
            return OrderPlan(False, 0, "no budget available under position/order limits")
        return OrderPlan(True, quantity, f"buy {quantity} @ {price:.2f} (budget {budget:.2f})")

    if side == "SELL":
        # Exits are risk-reducing, so the full held position is sold in one
        # order — capping a sell at max_order_value (an entry-risk control)
        # would leave part of a stop-loss or sell signal unexecuted.
        if held_quantity <= 0:
            return OrderPlan(False, 0, "no position held to sell")
        return OrderPlan(True, held_quantity, f"sell {held_quantity} @ {price:.2f} (full exit)")

    return OrderPlan(False, 0, f"unknown side: {side}")


def stop_loss_triggered(entry_price: float, current_price: float, risk: RiskConfig) -> bool:
    if entry_price <= 0:
        return False
    drop = (entry_price - current_price) / entry_price
    return drop >= risk.stop_loss_pct
