"""Core data structures shared across the purchase-list pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Product:
    """A single item as reported by a sourcing platform's catalog."""

    platform: str
    sku: str
    name: str
    cost_price: float
    recommended_retail_price: Optional[float]
    stock_qty: int
    category: str
    moq: int = 1
    sold_last_30d: Optional[int] = None
    image_url: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class ChannelFee:
    """Fee model used to estimate net margin on a given sales channel."""

    name: str
    commission_rate: float = 0.0
    payment_fee_rate: float = 0.0
    fixed_fee: float = 0.0

    def net_amount(self, sell_price: float) -> float:
        return sell_price * (1 - self.commission_rate - self.payment_fee_rate) - self.fixed_fee


@dataclass
class PurchaseListItem:
    """A scored recommendation row for the final purchase list."""

    product: Product
    channel: str
    target_sell_price: float
    estimated_margin: float
    margin_rate: float
    demand_score: float
    total_score: float
