"""Write the scored purchase list to a plain CSV file (audit trail / manual review)."""

from __future__ import annotations

import csv
from pathlib import Path

from purchase_pipeline.models import PurchaseListItem

FIELDNAMES = [
    "platform",
    "sku",
    "name",
    "category",
    "channel",
    "cost_price",
    "target_sell_price",
    "estimated_margin",
    "margin_rate",
    "stock_qty",
    "moq",
    "demand_score",
    "total_score",
    "image_url",
]


def write_purchase_list_csv(items: list[PurchaseListItem], path: str) -> str:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "platform": item.product.platform,
                    "sku": item.product.sku,
                    "name": item.product.name,
                    "category": item.product.category,
                    "channel": item.channel,
                    "cost_price": item.product.cost_price,
                    "target_sell_price": item.target_sell_price,
                    "estimated_margin": item.estimated_margin,
                    "margin_rate": item.margin_rate,
                    "stock_qty": item.product.stock_qty,
                    "moq": item.product.moq,
                    "demand_score": item.demand_score,
                    "total_score": item.total_score,
                    "image_url": item.product.image_url or "",
                }
            )

    return str(out_path)
