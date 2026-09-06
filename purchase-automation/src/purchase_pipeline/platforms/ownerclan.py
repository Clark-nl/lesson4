"""OwnerClan (오너클랜) sourcing-platform connector.

OwnerClan exposes an official Open API (OAuth2 client-credentials grant +
GraphQL catalog queries). Register API access from the OwnerClan seller
dashboard to obtain OWNERCLAN_CLIENT_ID / OWNERCLAN_CLIENT_SECRET.

Field names in the GraphQL query below follow OwnerClan's published Open
API docs at the time of writing; if OwnerClan changes their schema,
update `_CATALOG_QUERY` accordingly — everything downstream only depends
on the `Product` objects this module returns.

Mock mode: when no credentials are configured (or OWNERCLAN_MOCK=1 is
set), this connector reads `tests/fixtures/ownerclan_sample.json`
instead of calling the network, so the rest of the pipeline can be
built and tested before real API access is granted.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import requests

from purchase_pipeline.models import Product

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_URL = "https://auth.ownerclan.com/oauth2/token"
DEFAULT_API_URL = "https://api.ownerclan.com/v1/graphql"

_CATALOG_QUERY = """
query Items($first: Int!, $after: String) {
  items(first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        key
        name
        category { name }
        price
        marketPrice
        quantity
        minPurchaseQty
        sales30d
        image
      }
    }
  }
}
"""

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "ownerclan_sample.json"
)


class OwnerClanPlatform:
    name = "ownerclan"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        token_url: str = DEFAULT_TOKEN_URL,
        api_url: str = DEFAULT_API_URL,
        page_size: int = 100,
        mock: bool | None = None,
    ):
        self.client_id = client_id or os.environ.get("OWNERCLAN_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("OWNERCLAN_CLIENT_SECRET")
        self.token_url = token_url
        self.api_url = api_url
        self.page_size = page_size
        self._token: str | None = None
        self._token_expires_at: float = 0.0

        if mock is None:
            mock = os.environ.get("OWNERCLAN_MOCK") == "1" or not (
                self.client_id and self.client_secret
            )
        self.mock = mock
        if self.mock:
            logger.info("OwnerClanPlatform running in mock mode (fixture data, no network calls).")

    def fetch_catalog(self) -> list[Product]:
        if self.mock:
            return self._fetch_catalog_mock()
        return self._fetch_catalog_live()

    def _fetch_catalog_mock(self) -> list[Product]:
        raw_items = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
        return [self._to_product(item) for item in raw_items]

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        resp = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + payload.get("expires_in", 3600)
        return self._token

    def _fetch_catalog_live(self) -> list[Product]:
        products: list[Product] = []
        after: str | None = None
        while True:
            resp = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self._access_token()}"},
                json={
                    "query": _CATALOG_QUERY,
                    "variables": {"first": self.page_size, "after": after},
                },
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()
            if "errors" in payload:
                raise RuntimeError(f"OwnerClan API error: {payload['errors']}")

            data = payload["data"]["items"]
            for edge in data["edges"]:
                products.append(self._to_product(edge["node"]))

            page_info = data["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            after = page_info["endCursor"]

        return products

    def _to_product(self, node: dict) -> Product:
        category = node.get("category")
        category_name = category["name"] if isinstance(category, dict) else (category or "기타")
        return Product(
            platform=self.name,
            sku=str(node.get("key")),
            name=node.get("name", ""),
            cost_price=float(node.get("price", 0)),
            recommended_retail_price=(
                float(node["marketPrice"]) if node.get("marketPrice") else None
            ),
            stock_qty=int(node.get("quantity", 0)),
            category=category_name,
            moq=int(node.get("minPurchaseQty", 1) or 1),
            sold_last_30d=(
                int(node["sales30d"]) if node.get("sales30d") is not None else None
            ),
            image_url=node.get("image"),
            raw=node,
        )
