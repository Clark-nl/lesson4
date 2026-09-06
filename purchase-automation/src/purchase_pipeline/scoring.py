"""Turn a raw platform catalog into a ranked purchase list.

For each product/channel pair we estimate the net payout after that
channel's fees, derive a margin rate, blend it with a demand signal
(recent sales volume), and keep the top N rows above the configured
margin/stock thresholds.
"""

from __future__ import annotations

from purchase_pipeline.config import PipelineConfig
from purchase_pipeline.models import ChannelFee, Product, PurchaseListItem

# Fallback markup used only when a platform doesn't report a recommended
# retail price for an item.
DEFAULT_MARKUP = 1.8


def build_channel_fees(channel_fees_config: dict[str, dict]) -> dict[str, ChannelFee]:
    fees = {}
    for name, cfg in channel_fees_config.items():
        fees[name] = ChannelFee(
            name=name,
            commission_rate=cfg.get("commission_rate", 0.0),
            payment_fee_rate=cfg.get("payment_fee_rate", 0.0),
            fixed_fee=cfg.get("fixed_fee", 0.0),
        )
    return fees


def _target_sell_price(product: Product) -> float:
    if product.recommended_retail_price and product.recommended_retail_price > product.cost_price:
        return product.recommended_retail_price
    return round(product.cost_price * DEFAULT_MARKUP, 0)


def _demand_score(product: Product, max_sold: int) -> float:
    if not product.sold_last_30d or max_sold <= 0:
        return 0.0
    return min(product.sold_last_30d / max_sold, 1.0)


def score_products(products: list[Product], config: PipelineConfig) -> list[PurchaseListItem]:
    fees = build_channel_fees(config.channel_fees)
    max_sold = max((p.sold_last_30d or 0 for p in products), default=0)

    items: list[PurchaseListItem] = []
    for product in products:
        if product.stock_qty < config.scoring.min_stock_qty:
            continue

        sell_price = _target_sell_price(product)
        demand = _demand_score(product, max_sold)

        for channel in config.channels:
            fee = fees.get(channel, ChannelFee(name=channel))
            net = fee.net_amount(sell_price)
            margin = net - product.cost_price
            margin_rate = margin / sell_price if sell_price else 0.0

            if margin_rate < config.scoring.min_margin_rate:
                continue

            total_score = (
                config.scoring.margin_weight * margin_rate
                + config.scoring.demand_weight * demand
            )

            items.append(
                PurchaseListItem(
                    product=product,
                    channel=channel,
                    target_sell_price=sell_price,
                    estimated_margin=round(margin, 2),
                    margin_rate=round(margin_rate, 4),
                    demand_score=round(demand, 4),
                    total_score=round(total_score, 4),
                )
            )

    items.sort(key=lambda it: it.total_score, reverse=True)
    return items[: config.scoring.top_n]
