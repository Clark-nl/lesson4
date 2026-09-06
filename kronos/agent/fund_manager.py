"""Kronos: the fund manager agent.

Wires together, per symbol, on every cycle:

    price history -> Strategy -> Signal
                                    |
                                    v
                         RiskManager.validate_order  (hard caps, fails closed)
                                    |
                          (only if live_trading)
                                    v
                          ApprovalGate.confirm        (a human must type "yes")
                                    |
                                    v
                             Broker.place_order

When ``live_trading`` is False (the default), Kronos still runs the
full pipeline end to end against an in-memory FakeBroker, so you can
see exactly what it *would* have done without any risk.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from kronos.approval.human_approval import ApprovalGate, AutoDenyApprovalGate, CLIApprovalGate
from kronos.broker.base import Broker, Order, OrderResult, OrderSide
from kronos.broker.fake import FakeBroker
from kronos.config import KronosConfig
from kronos.data.market_data import get_price_history
from kronos.risk.guardrails import RiskManager, RiskViolation
from kronos.strategy.base import Action, Signal, Strategy
from kronos.strategy.vibe import VibeStrategy

logger = logging.getLogger("kronos.agent")

PriceHistoryFn = Callable[[str, str], pd.DataFrame]


@dataclass
class CycleResult:
    signal: Signal
    order: Order | None = None
    order_result: OrderResult | None = None
    skipped_reason: str | None = None


@dataclass
class DailyReport:
    net_liquidation: float
    cash_balance: float
    total_pnl_today: float
    orders_placed_today: int
    positions: list = field(default_factory=list)
    cycle_results: list[CycleResult] = field(default_factory=list)

    def as_text(self) -> str:
        lines = [
            "=== Kronos daily report ===",
            f"Net liquidation:   {self.net_liquidation:.2f}",
            f"Cash balance:      {self.cash_balance:.2f}",
            f"P&L today:         {self.total_pnl_today:+.2f}",
            f"Orders placed:     {self.orders_placed_today}",
            "",
            "Positions:",
        ]
        if not self.positions:
            lines.append("  (none)")
        for p in self.positions:
            lines.append(
                f"  {p.symbol}: {p.quantity} @ avg {p.average_cost:.2f}, "
                f"last {p.market_price:.2f}, unrealized {p.unrealized_pnl:+.2f}"
            )
        lines.append("")
        lines.append("This cycle's decisions:")
        for cr in self.cycle_results:
            summary = f"  {cr.signal.symbol}: {cr.signal.action.value} " \
                      f"(confidence {cr.signal.confidence:.2f})"
            if cr.skipped_reason:
                summary += f" -> skipped: {cr.skipped_reason}"
            elif cr.order_result:
                summary += f" -> {cr.order_result.status} ({cr.order_result.message})"
            lines.append(summary)
            for reason in cr.signal.reasons:
                lines.append(f"      - {reason}")
        return "\n".join(lines)


class Kronos:
    """The fund manager agent.

    Real money only ever moves if ALL of the following are true:
      1. ``config.live_trading`` is True (defaults to False).
      2. The candidate order passes every RiskManager check.
      3. A human explicitly approves the exact order via the ApprovalGate.
    """

    def __init__(
        self,
        config: KronosConfig,
        broker: Broker | None = None,
        strategy: Strategy | None = None,
        risk_manager: RiskManager | None = None,
        approval_gate: ApprovalGate | None = None,
        price_history_fn: PriceHistoryFn | None = None,
    ) -> None:
        self.config = config
        self.strategy = strategy or VibeStrategy()
        self.risk_manager = risk_manager or RiskManager(config.risk)
        self.price_history_fn = price_history_fn or (
            lambda symbol, exchange: get_price_history(symbol, exchange)
        )

        if broker is not None:
            self.broker = broker
        elif config.live_trading:
            from kronos.broker.ibkr import IBKRBroker

            self.broker = IBKRBroker(config.ibkr)
        else:
            self.broker = FakeBroker()

        if approval_gate is not None:
            self.approval_gate = approval_gate
        elif config.live_trading and config.require_human_approval:
            self.approval_gate = CLIApprovalGate()
        else:
            # Dry-run mode does not need a human gate: nothing real happens.
            self.approval_gate = AutoDenyApprovalGate()

        if config.live_trading and not config.require_human_approval:
            raise ValueError(
                "Refusing to build a live-trading Kronos with "
                "require_human_approval=False. Real-money orders must "
                "always be confirmed by a human."
            )

    def _position_value(self, symbol: str) -> float:
        for p in self.broker.get_positions():
            if p.symbol == symbol:
                return p.market_value
        return 0.0

    def _position_quantity(self, symbol: str) -> int:
        for p in self.broker.get_positions():
            if p.symbol == symbol:
                return p.quantity
        return 0

    def _size_order(self, side: OrderSide, symbol: str, reference_price: float) -> int:
        if side == OrderSide.SELL:
            return self._position_quantity(symbol)
        max_affordable = self.config.risk.max_order_value_eur / reference_price
        return max(0, int(max_affordable))

    def run_cycle(self, symbol: str) -> CycleResult:
        exchange = self.config.ibkr.exchange
        currency = self.config.ibkr.currency

        price_history = self.price_history_fn(symbol, exchange)
        signal = self.strategy.generate_signal(symbol, price_history)
        logger.info(
            "%s -> %s (confidence %.2f): %s",
            symbol,
            signal.action.value,
            signal.confidence,
            "; ".join(signal.reasons),
        )

        if signal.action == Action.HOLD:
            return CycleResult(signal=signal, skipped_reason="HOLD signal, no order generated")

        reference_price = float(price_history["close"].iloc[-1])
        side = OrderSide.BUY if signal.action == Action.BUY else OrderSide.SELL
        quantity = self._size_order(side, symbol, reference_price)

        if quantity <= 0:
            reason = (
                "no shares held to sell" if side == OrderSide.SELL
                else "position sizing produced zero shares (per-order limit too small "
                     "for current price)"
            )
            return CycleResult(signal=signal, skipped_reason=reason)

        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            exchange=exchange,
            currency=currency,
            reason=f"VibeStrategy signal ({signal.confidence:.2f} confidence): "
                   + "; ".join(signal.reasons),
        )

        account = self.broker.get_account_summary()
        current_position_value = self._position_value(symbol)

        try:
            self.risk_manager.validate_order(
                order, reference_price, account, current_position_value
            )
        except RiskViolation as exc:
            logger.warning("Order for %s rejected by RiskManager: %s", symbol, exc)
            return CycleResult(signal=signal, order=order, skipped_reason=str(exc))

        estimated_value = order.estimated_value(reference_price)

        if self.config.live_trading:
            approved = self.approval_gate.confirm(order, estimated_value, account)
            if not approved:
                return CycleResult(
                    signal=signal, order=order, skipped_reason="not approved by human"
                )

        result = self.broker.place_order(order)
        self.risk_manager.record_order_placed()
        logger.info("Order result for %s: %s (%s)", symbol, result.status, result.message)
        return CycleResult(signal=signal, order=order, order_result=result)

    def run_watchlist_cycle(self) -> DailyReport:
        cycle_results = [self.run_cycle(symbol) for symbol in self.config.watchlist]
        account = self.broker.get_account_summary()
        return DailyReport(
            net_liquidation=account.net_liquidation,
            cash_balance=account.cash_balance,
            total_pnl_today=account.total_pnl_today,
            orders_placed_today=self.risk_manager.orders_placed_today,
            positions=self.broker.get_positions(),
            cycle_results=cycle_results,
        )
