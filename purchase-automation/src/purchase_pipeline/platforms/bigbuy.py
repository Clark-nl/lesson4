"""BigBuy sourcing-platform connector.

BigBuy is a Spain-based EU dropshipping wholesaler with an EU warehouse
(no customs delay for NL/DE resale) and a public REST API. Register API
access from the BigBuy seller panel to obtain BIGBUY_API_KEY.

Field names below follow BigBuy's published REST API docs at the time
of writing (Bearer-token auth, JSON responses); if BigBuy changes their
response shape, update `_to_product()` accordingly — everything
downstream only depends on the `Product` objects this module returns.
Prices are in EUR.

Mock mode: when no API key is configured (or BIGBUY_MOCK=1 is set),
this connector reads `tests/fixtures/bigbuy_sample.json` instead of
calling the network, so the rest of the pipeline can be built and
tested before real API access is granted.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

from purchase_pipeline.models import Product

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.bigbuy.eu"

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "bigbuy_sample.json"
)


class BigBuyPlatform:
    name = "bigbuy"

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = DEFAULT_API_URL,
        page_size: int = 100,
        mock: bool | None = None,
    ):
        self.api_key = api_key or os.environ.get("BIGBUY_API_KEY")
        self.api_url = api_url
        self.page_size = page_size

        if mock is None:
            mock = os.environ.get("BIGBUY_MOCK") == "1" or not self.api_key
        self.mock = mock
        if self.mock:
            logger.info("BigBuyPlatform running in mock mode (fixture data, no network calls).")

    def fetch_catalog(self) -> list[Product]:
        if self.mock:
            return self._fetch_catalog_mock()
        return self._fetch_catalog_live()

    def _fetch_catalog_mock(self) -> list[Product]:
        raw_items = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
        return [self._to_product(item) for item in raw_items]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}

    def _fetch_catalog_live(self) -> list[Product]:
        products_by_id: dict[int, dict] = {}
        page = 0
        while True:
            resp = requests.get(
                f"{self.api_url}/rest/catalog/products.json",
                headers=self._headers(),
                params={"pageSize": self.page_size, "page": page},
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            for item in batch:
                products_by_id[item["id"]] = item
            if len(batch) < self.page_size:
                break
            page += 1

        stock_resp = requests.get(
            f"{self.api_url}/rest/catalog/productsstock.json",
            headers=self._headers(),
            timeout=60,
        )
        stock_resp.raise_for_status()
        stock_by_id = {row["id"]: row.get("quantity", 0) for row in stock_resp.json()}

        merged = []
        for product_id, item in products_by_id.items():
            item["quantity"] = stock_by_id.get(product_id, 0)
            merged.append(item)

        return [self._to_product(item) for item in merged]

    def _to_product(self, item: dict) -> Product:
        return Product(
            platform=self.name,
            sku=str(item.get("sku") or item.get("id")),
            name=item.get("name", ""),
            cost_price=float(item.get("wholesalePrice", 0)),
            recommended_retail_price=(
                float(item["retailPrice"]) if item.get("retailPrice") else None
            ),
            stock_qty=int(item.get("quantity", 0)),
            category=str(item.get("category", "Other")),
            moq=int(item.get("minQuantity", 1) or 1),
            sold_last_30d=None,  # BigBuy is a dropship supplier; no sales-velocity data available
            image_url=item.get("image"),
            raw=item,
        )
