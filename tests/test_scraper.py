import pathlib

import pytest

from zentrada_alert.scraper import (
    Product,
    ZentradaAuthError,
    ZentradaClient,
    filter_watched,
    parse_products,
)

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "sample_recommendations.html"


def test_parse_products_extracts_all_cards():
    html = FIXTURE.read_text(encoding="utf-8")

    products = parse_products(html)

    assert len(products) == 3
    assert products[0] == Product(
        name="Winter Jacket Unisex",
        price="€19.90",
        url="https://www.zentrada.com/product/1001",
    )


def test_filter_watched_returns_all_when_no_keywords():
    products = [Product(name="Toy Car", price="€5", url="")]

    assert filter_watched(products, []) == products


def test_filter_watched_matches_case_insensitively():
    products = [
        Product(name="Winter Jacket Unisex", price="€19.90", url=""),
        Product(name="Kids Toy Building Blocks", price="€8.50", url=""),
    ]

    result = filter_watched(products, ["jacket"])

    assert len(result) == 1
    assert result[0].name == "Winter Jacket Unisex"


class _FakeResponse:
    def __init__(self, url: str, text: str = ""):
        self.url = url
        self.text = text

    def raise_for_status(self):
        pass


class _FakeSession:
    def __init__(self, post_url: str, get_url: str = ""):
        self._post_url = post_url
        self._get_url = get_url

    def get(self, url, timeout=None):
        return _FakeResponse(self._get_url or url)

    def post(self, url, data=None, timeout=None):
        return _FakeResponse(self._post_url)


def test_login_raises_when_response_stays_on_login_page():
    session = _FakeSession(post_url="https://www.zentrada.com/login?error=1")
    client = ZentradaClient(session=session)

    with pytest.raises(ZentradaAuthError):
        client.login("user", "wrong-password")


def test_login_succeeds_when_redirected_away_from_login_page():
    session = _FakeSession(post_url="https://www.zentrada.com/dashboard")
    client = ZentradaClient(session=session)

    client.login("user", "correct-password")  # should not raise


def test_fetch_recommendations_html_raises_when_redirected_to_login():
    session = _FakeSession(
        post_url="https://www.zentrada.com/dashboard",
        get_url="https://www.zentrada.com/login",
    )
    client = ZentradaClient(session=session)

    with pytest.raises(ZentradaAuthError):
        client.fetch_recommendations_html()
