"""Shared CSV-parsing helper for feed/file-based platform connectors.

Any supplier that gives you a CSV (a dropXL account feed, a Syncee/any
marketplace "export catalog" button, a manually-typed spreadsheet) can be
turned into `Product` objects with this one function plus a column_map
describing which of your CSV's headers hold which field.
"""

from __future__ import annotations

import csv
import io

from purchase_pipeline.models import Product

# Default header names this pipeline looks for when you don't override
# column_map. Edit column_map (not this) to match your actual file.
DEFAULT_CSV_COLUMN_MAP = {
    "sku": "sku",
    "name": "name",
    "wholesale_price": "wholesale_price",
    "retail_price": "retail_price",
    "stock": "stock",
    "category": "category",
}


def parse_csv_products(text: str, column_map: dict[str, str], platform_name: str) -> list[Product]:
    reader = csv.DictReader(io.StringIO(text))
    return [_row_to_product(row, column_map, platform_name) for row in reader]


def _row_to_product(row: dict, column_map: dict[str, str], platform_name: str) -> Product:
    col = column_map
    return Product(
        platform=platform_name,
        sku=row.get(col["sku"], ""),
        name=row.get(col["name"], ""),
        cost_price=float(row.get(col["wholesale_price"]) or 0),
        recommended_retail_price=(
            float(row[col["retail_price"]]) if row.get(col["retail_price"]) else None
        ),
        stock_qty=int(float(row.get(col["stock"]) or 0)),
        category=row.get(col["category"], "Other"),
        moq=1,
        sold_last_30d=None,  # plain CSV exports don't carry sales-velocity data
        image_url=row.get("image_url") or row.get("image"),
        raw=row,
    )
