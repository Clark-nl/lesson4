from purchase_pipeline.platforms.syncee import SynceePlatform


def test_mock_mode_reads_shopify_catalog_fixture():
    platform = SynceePlatform(mock=True)

    products = platform.fetch_catalog()

    # Product SY-113 has no "Cost per item" set in Shopify (no matching
    # inventory_items entry) so it can't be scored and must be skipped.
    assert {p.sku for p in products} == {"SY-111", "SY-112", "SY-114"}

    lantern = next(p for p in products if p.sku == "SY-111")
    assert lantern.name == "Garden Solar Lantern"
    assert lantern.cost_price == 9.20
    assert lantern.recommended_retail_price == 24.95
    assert lantern.stock_qty == 60
    assert lantern.category == "Garden"


def test_defaults_to_mock_mode_without_shopify_credentials(monkeypatch):
    monkeypatch.delenv("SHOPIFY_SHOP", raising=False)
    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SYNCEE_MOCK", raising=False)

    platform = SynceePlatform()

    assert platform.mock is True
    assert len(platform.fetch_catalog()) == 3
