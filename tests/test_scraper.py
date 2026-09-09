import pathlib

from zentrada_alert.scraper import Product, filter_watched, parse_products

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
