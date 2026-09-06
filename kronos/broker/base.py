"""Broker-agnostic data model and interface.

Any real broker integration (IBKR, Saxo, ...) implements the ``Broker``
interface below. This keeps the strategy/risk/agent layers free of any
vendor-specific SDK details, and makes it possible to test the whole
pipeline against a fake broker.
"""
from __future__ import annotations

import abc
import enum
from dataclasses import dataclass
from datetime import datetime


class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: int
    exchange: str = "AEB"
    currency: str = "EUR"
    order_type: str = "MKT"
    limit_price: float | None = None
    reason: str = ""
    created_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")

    def estimated_value(self, reference_price: float) -> float:
        return abs(self.quantity) * reference_price


@dataclass
class Position:
    symbol: str
    quantity: int
    average_cost: float
    market_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.market_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.market_price - self.average_cost) * self.quantity


@dataclass
class AccountSummary:
    net_liquidation: float
    cash_balance: float
    realized_pnl_today: float
    unrealized_pnl_today: float
    currency: str = "EUR"

    @property
    def total_pnl_today(self) -> float:
        return self.realized_pnl_today + self.unrealized_pnl_today


@dataclass
class OrderResult:
    order: Order
    status: str  # e.g. "SUBMITTED", "FILLED", "REJECTED", "SIMULATED"
    broker_order_id: str | None = None
    fill_price: float | None = None
    message: str = ""


class Broker(abc.ABC):
    """Minimal interface Kronos needs from a broker connection."""

    @abc.abstractmethod
    def connect(self) -> None:
        ...

    @abc.abstractmethod
    def disconnect(self) -> None:
        ...

    @abc.abstractmethod
    def get_account_summary(self) -> AccountSummary:
        ...

    @abc.abstractmethod
    def get_positions(self) -> list[Position]:
        ...

    @abc.abstractmethod
    def get_last_price(self, symbol: str, exchange: str, currency: str) -> float:
        ...

    @abc.abstractmethod
    def place_order(self, order: Order) -> OrderResult:
        """Submit a real order. Must only ever be called after risk checks
        and human approval have both passed."""
        ...

    def __enter__(self) -> "Broker":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()
