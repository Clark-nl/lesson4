from purchase_pipeline.platforms.ownerclan import OwnerClanPlatform


def test_mock_mode_loads_fixture_catalog():
    platform = OwnerClanPlatform(mock=True)

    products = platform.fetch_catalog()

    assert len(products) == 5
    first = next(p for p in products if p.sku == "OC-1001")
    assert first.name == "무선 이어폰 케이스"
    assert first.cost_price == 8000
    assert first.recommended_retail_price == 19900
    assert first.stock_qty == 120
    assert first.category == "전자기기"


def test_defaults_to_mock_mode_without_credentials(monkeypatch):
    monkeypatch.delenv("OWNERCLAN_CLIENT_ID", raising=False)
    monkeypatch.delenv("OWNERCLAN_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OWNERCLAN_MOCK", raising=False)

    platform = OwnerClanPlatform()

    assert platform.mock is True
    assert len(platform.fetch_catalog()) == 5
