"""Fetches and parses expected-purchase items from Zentrada."""
import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from zentrada_alert import config

logger = logging.getLogger(__name__)


@dataclass
class Product:
    name: str
    price: str
    url: str
    sku: str = ""


class ZentradaAuthError(RuntimeError):
    """Raised when login to Zentrada fails."""


class ZentradaClient:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def login(self, username: str, password: str) -> None:
        login_url = urljoin(config.ZENTRADA_BASE_URL, config.ZENTRADA_LOGIN_PATH)

        # Load the login page first in case it carries a CSRF token cookie.
        self.session.get(login_url, timeout=config.REQUEST_TIMEOUT_SECONDS)

        response = self.session.post(
            login_url,
            data={
                config.LOGIN_FORM_USERNAME_FIELD: username,
                config.LOGIN_FORM_PASSWORD_FIELD: password,
            },
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    def fetch_recommendations_html(self) -> str:
        url = urljoin(config.ZENTRADA_BASE_URL, config.ZENTRADA_RECOMMENDATIONS_PATH)
        response = self.session.get(url, timeout=config.REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text

    def fetch_expected_purchase_items(self) -> list[Product]:
        html = self.fetch_recommendations_html()
        return parse_products(html)


def parse_products(html: str) -> list[Product]:
    """Parses product cards out of a recommendations/listing page.

    Selectors come from config so the caller can adapt to the real site
    markup without touching this code.
    """
    soup = BeautifulSoup(html, "html.parser")
    products: list[Product] = []

    for card in soup.select(config.SELECTOR_PRODUCT_CARD):
        name_el = card.select_one(config.SELECTOR_PRODUCT_NAME)
        price_el = card.select_one(config.SELECTOR_PRODUCT_PRICE)
        link_el = card.select_one(config.SELECTOR_PRODUCT_LINK)

        if name_el is None:
            logger.debug("Skipping product card with no name element: %s", card)
            continue

        sku = ""
        if config.SELECTOR_PRODUCT_SKU:
            sku_el = card.select_one(config.SELECTOR_PRODUCT_SKU)
            sku = sku_el.get_text(strip=True) if sku_el else ""

        href = link_el.get("href", "") if link_el else ""
        url = urljoin(config.ZENTRADA_BASE_URL, href) if href else ""

        products.append(
            Product(
                name=name_el.get_text(strip=True),
                price=price_el.get_text(strip=True) if price_el else "",
                url=url,
                sku=sku,
            )
        )

    return products


def filter_watched(products: list[Product], keywords: list[str]) -> list[Product]:
    """Narrows the list down to items matching WATCH_KEYWORDS.

    With no keywords configured, every recommended item counts as an
    "expected purchase item".
    """
    if not keywords:
        return products

    lowered_keywords = [k.lower() for k in keywords]
    return [
        product
        for product in products
        if any(keyword in product.name.lower() for keyword in lowered_keywords)
    ]
