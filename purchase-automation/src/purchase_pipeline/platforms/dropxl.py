"""dropXL (formerly dropshippingXL, by vidaXL) sourcing-platform connector.

What's confirmed via primary/press sources: vidaXL is a real, ~20-year-old
Dutch home/garden/sports retailer (Venlo, Netherlands; $400M+ revenue,
1,000-5,000 employees; 90,000+ products), and its dropship program
rebranded from "dropshippingXL" to "dropXL" in October 2025. Search
results (dodropshipping.com, bootstrappingecommerce.com, dropxl.com's own
integrations page) describe: a flat EUR30/month subscription (no per-sale
commission), CSV/XML product feeds updated hourly for stock and daily for
price, plus an account-scoped API used mainly to push orders back to
dropXL. Being NL-based, it ships fastest specifically to the Netherlands
of any option evaluated for this pipeline (vs. BigBuy's ~2-3 days from
Spain) — but the catalog is limited to home/garden/sports/toys, not
category-agnostic like BigBuy or Zentrada.

What's NOT confirmed: nobody here has an actual dropXL account, and the
exact feed URL / column names are assigned per-account (dropXL account
settings), not documented in any public page this session could reach.
So unlike ownerclan.py/bigbuy.py, this connector does NOT hardcode a
base URL or field names — it fetches whatever feed URL you paste into
DROPXL_FEED_URL (copy it from your dropXL account settings) and maps
columns using CSV_COLUMN_MAP below, which you should edit to match your
actual feed's header row once you have a real account. Guessing exact
column names here would just be a second unverified guess dressed up as
code, which is exactly what BigBuy's connector already got called out
for once - so this one is deliberately configurable instead.

Mock mode: when no feed URL is configured (or DROPXL_MOCK=1 is set),
this connector reads `tests/fixtures/dropxl_sample.csv` (using the
default CSV_COLUMN_MAP) instead of calling the network.
"""

from __future__ import annotations

import csv
import io
import logging
import os
from pathlib import Path

import requests

from purchase_pipeline.models import Product

logger = logging.getLogger(__name__)

# Edit these to match your actual dropXL feed's header row.
DEFAULT_CSV_COLUMN_MAP = {
    "sku": "sku",
    "name": "name",
    "wholesale_price": "wholesale_price",
    "retail_price": "retail_price",
    "stock": "stock",
    "category": "category",
}

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "dropxl_sample.csv"
)


class DropXLPlatform:
    name = "dropxl"

    def __init__(
        self,
        feed_url: str | None = None,
        api_key: str | None = None,
        column_map: dict[str, str] | None = None,
        mock: bool | None = None,
    ):
        self.feed_url = feed_url or os.environ.get("DROPXL_FEED_URL")
        self.api_key = api_key or os.environ.get("DROPXL_API_KEY")
        self.column_map = column_map or dict(DEFAULT_CSV_COLUMN_MAP)

        if mock is None:
            mock = os.environ.get("DROPXL_MOCK") == "1" or not self.feed_url
        self.mock = mock
        if self.mock:
            logger.info("DropXLPlatform running in mock mode (fixture data, no network calls).")

    def fetch_catalog(self) -> list[Product]:
        if self.mock:
            return self._parse_csv(_FIXTURE_PATH.read_text(encoding="utf-8"))
        return self._fetch_catalog_live()

    def _fetch_catalog_live(self) -> list[Product]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        resp = requests.get(self.feed_url, headers=headers, timeout=60)
        resp.raise_for_status()
        return self._parse_csv(resp.text)

    def _parse_csv(self, text: str) -> list[Product]:
        reader = csv.DictReader(io.StringIO(text))
        return [self._to_product(row) for row in reader]

    def _to_product(self, row: dict) -> Product:
        col = self.column_map
        return Product(
            platform=self.name,
            sku=row.get(col["sku"], ""),
            name=row.get(col["name"], ""),
            cost_price=float(row.get(col["wholesale_price"]) or 0),
            recommended_retail_price=(
                float(row[col["retail_price"]]) if row.get(col["retail_price"]) else None
            ),
            stock_qty=int(float(row.get(col["stock"]) or 0)),
            category=row.get(col["category"], "Other"),
            moq=1,  # dropXL is a single-unit dropship feed; no MOQ column expected
            sold_last_30d=None,  # no sales-velocity data in the product feed
            image_url=row.get("image_url") or row.get("image"),
            raw=row,
        )
