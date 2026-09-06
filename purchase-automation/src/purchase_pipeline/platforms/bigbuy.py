"""BigBuy sourcing-platform connector.

What's confirmed via primary sources (Wikipedia, Spanish business press —
Valencia Plaza, Emprendedores): BigBuy is a real company, founded 2012 in
Valencia, Spain (founders Salvador Esteve and Victor P. Amarnani), ~30,000 m2
own warehouse in Moncada, ~300,000 SKUs across 20+ categories, EUR110M
revenue (2022), 95% exported mostly within Europe. Search results also
show BigBuy hosts its own developer-API landing page and PDF guide on its
own domain (bigbuy.eu/en/api_bigbuy.html, bigbuy.eu/public/doc/Guia_API_
BigBuy_EN.pdf) — i.e. the API is BigBuy's own first-party offering, not a
third party's.

What's NOT independently confirmed: this session's network policy blocks
bigbuy.eu outright, so nobody here has actually read that PDF guide or
hit the live API. The endpoint paths, auth header, and field names coded
below (base URL `https://api.bigbuy.eu/rest/catalog/`, `Authorization:
Bearer <token>`, `products.json`/`productsstock.json`, `wholesalePrice`/
`retailPrice`/`sku`/`category`, stock nested as `stocks: [{quantity:
...}]`) come from reading public third-party integration code that claims
to implement that same official API — not from the official docs
themselves. Treat this as a well-informed best guess, not a verified
contract: before relying on it, get real BIGBUY_API_KEY, hit
`products.json` once, and confirm the response actually looks like what
`_to_product()` below expects. Images are apparently a separate
`productsimages.json` endpoint per the API's own landing page, so
`image_url` here only picks up an `image`/`images` field if `products.json`
happens to already include one — call that endpoint too and merge it in
if you need images reliably. If the real shape differs, only
`_to_product()` (and the two requests in `_fetch_catalog_live()`) need to
change — everything downstream only depends on the `Product` objects this
module returns. Prices are in EUR.

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
SANDBOX_API_URL = "https://api.sandbox.bigbuy.eu"

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "bigbuy_sample.json"
)


class BigBuyPlatform:
    name = "bigbuy"

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = DEFAULT_API_URL,
        mock: bool | None = None,
    ):
        self.api_key = api_key or os.environ.get("BIGBUY_API_KEY")
        self.api_url = api_url

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
        products_resp = requests.get(
            f"{self.api_url}/rest/catalog/products.json",
            headers=self._headers(),
            params={"isoCode": "en"},
            timeout=60,
        )
        products_resp.raise_for_status()
        products_by_id = {item["id"]: item for item in products_resp.json()}

        stock_resp = requests.get(
            f"{self.api_url}/rest/catalog/productsstock.json",
            headers=self._headers(),
            params={"isoCode": "en"},
            timeout=60,
        )
        stock_resp.raise_for_status()
        stock_by_id = {
            row["id"]: (row["stocks"][0]["quantity"] if row.get("stocks") else 0)
            for row in stock_resp.json()
        }

        merged = []
        for product_id, item in products_by_id.items():
            item["quantity"] = stock_by_id.get(product_id, 0)
            merged.append(item)

        return [self._to_product(item) for item in merged]

    def _to_product(self, item: dict) -> Product:
        images = item.get("images") or []
        image_url = item.get("image") or (images[0] if images else None)
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
            # BigBuy dropship MOQ field name is unverified against the official
            # PDF guide; falls back to 1 (no minimum) if absent either way.
            moq=int(item.get("minQuantity", 1) or 1),
            sold_last_30d=None,  # BigBuy is a dropship supplier; no sales-velocity data available
            image_url=image_url,
            raw=item,
        )
