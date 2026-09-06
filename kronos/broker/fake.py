"""In-memory broker used for dry-run mode, backtests and tests.

Never touches the network. Kronos uses this automatically whenever
``live_trading`` is False, so the whole pipeline (data -> strategy ->
risk -> approval -> "execution") can run safely end to end without an
IBKR connection.
"""
from __future__ import annotations

from kronos.broker.base import AccountSummary, Broker, Order, OrderResult, OrderSide, Position


class FakeBroker(Broker):
    def __init__(
        self,
        starting_cash: float = 10_000.0,
        prices: dict[str, float] | None = None,
    ) -> None:
        self.cash = starting_cash
        self.prices = prices or {}
        self.positions: dict[str, Position] = {}
        self.realized_pnl_today = 0.0
        self.orders: list[Order] = []
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def set_price(self, symbol: str, price: float) -> None:
        self.prices[symbol] = price
        if symbol in self.positions:
            pos = self.positions[symbol]
            self.positions[symbol] = Position(
                symbol=pos.symbol,
                quantity=pos.quantity,
                average_cost=pos.average_cost,
                market_price=price,
            )

    def get_account_summary(self) -> AccountSummary:
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        net_liq = self.cash + sum(p.market_value for p in self.positions.values())
        return AccountSummary(
            net_liquidation=net_liq,
            cash_balance=self.cash,
            realized_pnl_today=self.realized_pnl_today,
            unrealized_pnl_today=unrealized,
        )

    def get_positions(self) -> list[Position]:
        return list(self.positions.values())

    def get_last_price(self, symbol: str, exchange: str, currency: str) -> float:
        if symbol not in self.prices:
            raise RuntimeError(f"No simulated price set for {symbol}")
        return self.prices[symbol]

    def place_order(self, order: Order) -> OrderResult:
        price = self.get_last_price(order.symbol, order.exchange, order.currency)
        value = order.estimated_value(price)
        current = self.positions.get(order.symbol)
        current_qty = current.quantity if current else 0
        current_cost = current.average_cost if current else 0.0

        if order.side == OrderSide.BUY:
            new_qty = current_qty + order.quantity
            new_cost = (
                (current_qty * current_cost) + (order.quantity * price)
            ) / new_qty
            self.cash -= value
            self.positions[order.symbol] = Position(
                symbol=order.symbol,
                quantity=new_qty,
                average_cost=new_cost,
                market_price=price,
            )
        else:
            new_qty = current_qty - order.quantity
            realized = (price - current_cost) * min(order.quantity, current_qty)
            self.realized_pnl_today += realized
            self.cash += value
            if new_qty > 0:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=new_qty,
                    average_cost=current_cost,
                    market_price=price,
                )
            else:
                self.positions.pop(order.symbol, None)

        self.orders.append(order)
        return OrderResult(
            order=order,
            status="SIMULATED",
            broker_order_id=f"SIM-{len(self.orders)}",
            fill_price=price,
            message="Simulated fill (dry-run / paper mode)",
        )
