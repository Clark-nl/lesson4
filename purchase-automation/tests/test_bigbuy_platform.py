from purchase_pipeline.platforms.bigbuy import BigBuyPlatform


def test_mock_mode_loads_fixture_catalog():
    platform = BigBuyPlatform(mock=True)

    products = platform.fetch_catalog()

    assert len(products) == 5
    first = next(p for p in products if p.sku == "BB-2001")
    assert first.name == "Wireless Earbuds Charging Case"
    assert first.cost_price == 6.80
    assert first.recommended_retail_price == 19.95
    assert first.stock_qty == 300
    assert first.category == "Electronics"
    assert first.sold_last_30d is None


def test_defaults_to_mock_mode_without_credentials(monkeypatch):
    monkeypatch.delenv("BIGBUY_API_KEY", raising=False)
    monkeypatch.delenv("BIGBUY_MOCK", raising=False)

    platform = BigBuyPlatform()

    assert platform.mock is True
    assert len(platform.fetch_catalog()) == 5
