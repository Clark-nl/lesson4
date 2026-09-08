"""JSON 파일 기반의 간단한 상품/주문 저장소.

실제 서비스에서는 이 모듈을 DB 접근 계층으로 교체하면 된다.
"""

import json
from typing import Any

from . import config


def load_catalog() -> list[dict[str, Any]]:
    with open(config.CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_orders() -> list[dict[str, Any]]:
    with open(config.ORDERS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_orders(orders: list[dict[str, Any]]) -> None:
    with open(config.ORDERS_PATH, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def find_product(product_id: str) -> dict[str, Any] | None:
    for product in load_catalog():
        if product["id"] == product_id:
            return product
    return None


def find_order(order_id: str) -> dict[str, Any] | None:
    for order in load_orders():
        if order["order_id"] == order_id:
            return order
    return None
