"""Generic bulk-upload CSV template for open-market channels (쿠팡/네이버/이베이).

Coupang Wing and Naver Commerce API both require per-seller category
mapping and API approval before you can push listings programmatically,
so this exporter targets the common ground instead: a CSV shaped close
to each marketplace's bulk-upload template, ready for a seller to
review and import through the marketplace's own bulk-upload screen (or
to be fed into that marketplace's API once approved, by mapping these
columns onto the API payload).
"""

from __future__ import annotations

import csv
from pathlib import Path

from purchase_pipeline.models import PurchaseListItem

FIELDNAMES = [
    "sku",
    "product_name",
    "category",
    "sale_price",
    "cost_price",
    "stock_qty",
    "min_order_qty",
    "image_url",
    "channel",
]


def write_marketplace_csv(items: list[PurchaseListItem], path: str, channel: str) -> str:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [item for item in items if item.channel == channel]
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "sku": item.product.sku,
                    "product_name": item.product.name,
                    "category": item.product.category,
                    "sale_price": item.target_sell_price,
                    "cost_price": item.product.cost_price,
                    "stock_qty": item.product.stock_qty,
                    "min_order_qty": item.product.moq,
                    "image_url": item.product.image_url or "",
                    "channel": item.channel,
                }
            )

    return str(out_path)
