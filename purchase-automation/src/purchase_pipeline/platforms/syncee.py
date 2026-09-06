"""Syncee sourcing "connector" — actually reads back your own Shopify catalog.

Important: this does NOT call a Syncee API, because Syncee doesn't expose
one to merchants. Confirmed via research: Syncee is a Shopify/WooCommerce
*app* — installed in your store, it syncs supplier products (including
their EU-warehouse ones, filterable in the app) directly into your
store's own product catalog. There is no separate merchant-facing REST
API to poll, unlike OwnerClan/BigBuy/dropXL. Pretending otherwise here
would just be a third unverified-API guess, which is exactly what this
pipeline has already been called out for once with BigBuy.

What this connector does instead: once Syncee has synced products into
Shopify, the wholesale cost Syncee filled in lives on Shopify's own
"Cost per item" field (the InventoryItem.cost field in Shopify's Admin
API), and the price you're already selling at is the variant's `price`.
So `fetch_catalog()` here just reads your Shopify store's own catalog via
the Shopify Admin REST API — the same SHOPIFY_SHOP/SHOPIFY_ACCESS_TOKEN
credentials already used by `exporters/shopify_exporter.py`, requiring
`read_products`/`read_inventory` scopes. No new platform subscription or
API key is needed beyond Shopify (which you already have) and whatever
Syncee plan you use to get products into the store in the first place —
which is the cheapest architecture available for this pipeline.

Because of this, the "shopify" channel should NOT be listed in a config
using this platform (the store is the source, not an export target) —
use it to decide what to additionally cross-list on marketplace channels
like amazon_nl/amazon_de instead. See config.syncee.example.yaml.

Mock mode: when no Shopify credentials are configured (or SYNCEE_MOCK=1
is set), reads `tests/fixtures/syncee_shopify_sample.json` (a products.json
+ inventory_items.json shaped fixture) instead of calling the network.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

from purchase_pipeline.models import Product

logger = logging.getLogger(__name__)

API_VERSION = "2024-10"

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "syncee_shopify_sample.json"
)


class SynceePlatform:
    name = "syncee"

    def __init__(
        self,
        shop: str | None = None,
        access_token: str | None = None,
        mock: bool | None = None,
    ):
        self.shop = shop or os.environ.get("SHOPIFY_SHOP")
        self.access_token = access_token or os.environ.get("SHOPIFY_ACCESS_TOKEN")

        if mock is None:
            mock = os.environ.get("SYNCEE_MOCK") == "1" or not (self.shop and self.access_token)
        self.mock = mock
        if self.mock:
            logger.info("SynceePlatform running in mock mode (fixture data, no network calls).")

    def fetch_catalog(self) -> list[Product]:
        if self.mock:
            fixture = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
            return self._build_products(fixture["products"], fixture["inventory_items"])
        return self._fetch_catalog_live()

    def _headers(self) -> dict:
        return {"X-Shopify-Access-Token": self.access_token, "Accept": "application/json"}

    def _fetch_catalog_live(self) -> list[Product]:
        products: list[dict] = []
        url = f"https://{self.shop}/admin/api/{API_VERSION}/products.json"
        params = {"limit": 250}
        while url:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
            resp.raise_for_status()
            products.extend(resp.json().get("products", []))
            url, params = _next_page(resp)

        inventory_item_ids = [
            str(variant["inventory_item_id"])
            for product in products
            for variant in product.get("variants", [])
            if variant.get("inventory_item_id")
        ]
        inventory_items = self._fetch_inventory_items(inventory_item_ids)

        return self._build_products(products, inventory_items)

    def _fetch_inventory_items(self, ids: list[str]) -> list[dict]:
        items: list[dict] = []
        # Shopify limits inventory_items.json to 250 ids per request.
        for i in range(0, len(ids), 250):
            chunk = ids[i : i + 250]
            resp = requests.get(
                f"https://{self.shop}/admin/api/{API_VERSION}/inventory_items.json",
                headers=self._headers(),
                params={"ids": ",".join(chunk)},
                timeout=30,
            )
            resp.raise_for_status()
            items.extend(resp.json().get("inventory_items", []))
        return items

    def _build_products(self, products: list[dict], inventory_items: list[dict]) -> list[Product]:
        cost_by_inventory_item_id = {
            item["id"]: float(item["cost"]) for item in inventory_items if item.get("cost")
        }

        result = []
        for product in products:
            category = product.get("product_type") or "Other"
            image_url = (product.get("image") or {}).get("src")
            for variant in product.get("variants", []):
                cost = cost_by_inventory_item_id.get(variant.get("inventory_item_id"))
                if cost is None:
                    # No "Cost per item" set on this variant (Syncee didn't fill it
                    # in, or it was cleared) - can't compute margin, so skip it.
                    continue
                result.append(
                    Product(
                        platform=self.name,
                        sku=variant.get("sku") or str(variant["id"]),
                        name=product.get("title", ""),
                        cost_price=cost,
                        recommended_retail_price=float(variant["price"]),
                        stock_qty=int(variant.get("inventory_quantity") or 0),
                        category=category,
                        moq=1,
                        sold_last_30d=None,  # would need the Orders API; not fetched here
                        image_url=image_url,
                        raw={"product": product, "variant": variant},
                    )
                )
        return result


def _next_page(resp: requests.Response) -> tuple[str | None, dict | None]:
    link = resp.headers.get("Link", "")
    for part in link.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip(" <>"), None
    return None, None
