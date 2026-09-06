from purchase_pipeline.platforms.dropxl import DropXLPlatform


def test_mock_mode_parses_fixture_csv():
    platform = DropXLPlatform(mock=True)

    products = platform.fetch_catalog()

    assert len(products) == 5
    first = next(p for p in products if p.sku == "DXL-3001")
    assert first.name == "Garden Storage Box 400L"
    assert first.cost_price == 24.50
    assert first.recommended_retail_price == 59.95
    assert first.stock_qty == 80
    assert first.category == "Garden"
    assert first.moq == 1
    assert first.sold_last_30d is None


def test_defaults_to_mock_mode_without_feed_url(monkeypatch):
    monkeypatch.delenv("DROPXL_FEED_URL", raising=False)
    monkeypatch.delenv("DROPXL_MOCK", raising=False)

    platform = DropXLPlatform()

    assert platform.mock is True
    assert len(platform.fetch_catalog()) == 5


def test_custom_column_map_for_a_differently_shaped_feed():
    csv_text = "SKU,Name,PurchasePrice,RRP,QtyInStock,Category\nX1,Widget,1.5,4.0,10,Misc\n"
    platform = DropXLPlatform(
        mock=True,
        column_map={
            "sku": "SKU",
            "name": "Name",
            "wholesale_price": "PurchasePrice",
            "retail_price": "RRP",
            "stock": "QtyInStock",
            "category": "Category",
        },
    )

    products = platform._parse_csv(csv_text)

    assert len(products) == 1
    assert products[0].sku == "X1"
    assert products[0].cost_price == 1.5
    assert products[0].stock_qty == 10
