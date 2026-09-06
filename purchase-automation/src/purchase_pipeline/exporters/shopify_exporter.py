"""Push scored purchase-list rows into Shopify as draft products.

Requires SHOPIFY_SHOP (e.g. "my-store.myshopify.com") and
SHOPIFY_ACCESS_TOKEN (a custom-app Admin API access token with
write_products scope). Runs in dry-run mode (logs only, no network
calls) when those aren't set, so the pipeline stays runnable without
live credentials.
"""

from __future__ import annotations

import logging
import os

import requests

from purchase_pipeline.models import PurchaseListItem

logger = logging.getLogger(__name__)

API_VERSION = "2024-10"


def push_draft_products(items: list[PurchaseListItem], channel: str = "shopify") -> list[str]:
    shop = os.environ.get("SHOPIFY_SHOP")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    rows = [item for item in items if item.channel == channel]

    if not shop or not token:
        logger.info(
            "SHOPIFY_SHOP/SHOPIFY_ACCESS_TOKEN not set — dry run, would create %d draft products.",
            len(rows),
        )
        return []

    url = f"https://{shop}/admin/api/{API_VERSION}/products.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    created_ids: list[str] = []

    for item in rows:
        payload = {
            "product": {
                "title": item.product.name,
                "product_type": item.product.category,
                "status": "draft",
                "variants": [
                    {
                        "sku": item.product.sku,
                        "price": f"{item.target_sell_price:.2f}",
                        "inventory_quantity": item.product.stock_qty,
                        "inventory_management": "shopify",
                    }
                ],
                "images": [{"src": item.product.image_url}] if item.product.image_url else [],
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code >= 300:
            logger.warning("Shopify draft creation failed for %s: %s", item.product.sku, resp.text)
            continue
        created_ids.append(str(resp.json()["product"]["id"]))

    logger.info("Created %d Shopify draft products.", len(created_ids))
    return created_ids
