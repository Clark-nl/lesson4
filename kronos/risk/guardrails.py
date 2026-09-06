"""Hard risk limits that stand between a strategy signal and a real order.

The RiskManager is deliberately conservative and fails *closed*: if it
cannot prove an order is within limits, it rejects it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from kronos.broker.base import AccountSummary, Order
from kronos.config import RiskLimits


class RiskViolation(Exception):
    """Raised when an order or the account state breaches a hard limit."""


@dataclass
class _DailyCounters:
    day: date = field(default_factory=date.today)
    orders_placed: int = 0

    def roll_if_new_day(self) -> None:
        today = date.today()
        if today != self.day:
            self.day = today
            self.orders_placed = 0


class RiskManager:
    """Enforces per-order, per-day and per-position caps.

    This class never talks to a broker itself; it is handed the current
    account summary and asked to approve or reject a candidate order and
    its estimated value.
    """

    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits
        self._counters = _DailyCounters()

    def validate_order(
        self,
        order: Order,
        reference_price: float,
        account: AccountSummary,
        current_position_value: float = 0.0,
    ) -> None:
        """Raise ``RiskViolation`` if the order breaks any hard limit.

        Returns normally if the order is within all configured limits.
        """
        self._counters.roll_if_new_day()

        if reference_price <= 0:
            raise RiskViolation(f"Invalid reference price for {order.symbol}: {reference_price}")

        order_value = order.estimated_value(reference_price)

        if order_value > self.limits.max_order_value_eur:
            raise RiskViolation(
                f"Order value {order_value:.2f} EUR exceeds per-order limit "
                f"of {self.limits.max_order_value_eur:.2f} EUR for {order.symbol}"
            )

        if self._counters.orders_placed >= self.limits.max_orders_per_day:
            raise RiskViolation(
                f"Daily order count limit reached "
                f"({self.limits.max_orders_per_day} orders/day)"
            )

        if account.total_pnl_today <= -abs(self.limits.max_daily_loss_eur):
            raise RiskViolation(
                f"Daily loss limit breached: {account.total_pnl_today:.2f} EUR "
                f"<= -{self.limits.max_daily_loss_eur:.2f} EUR. "
                "No further orders will be placed today."
            )

        if order.side.value == "BUY":
            projected_position_value = current_position_value + order_value
            if projected_position_value > self.limits.max_position_value_eur:
                raise RiskViolation(
                    f"Projected position value {projected_position_value:.2f} EUR "
                    f"would exceed max position value "
                    f"{self.limits.max_position_value_eur:.2f} EUR for {order.symbol}"
                )

        if order_value > account.cash_balance and order.side.value == "BUY":
            raise RiskViolation(
                f"Insufficient cash: order value {order_value:.2f} EUR > "
                f"available cash {account.cash_balance:.2f} EUR"
            )

    def record_order_placed(self) -> None:
        self._counters.roll_if_new_day()
        self._counters.orders_placed += 1

    @property
    def orders_placed_today(self) -> int:
        self._counters.roll_if_new_day()
        return self._counters.orders_placed
