from purchase_pipeline.exporters import shopify_exporter
from purchase_pipeline.models import Product, PurchaseListItem


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200, headers=None, text=""):
        self._json = json_data or {}
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http error {self.status_code}")


class _FakeSession:
    def __init__(self, existing_skus):
        self._existing_skus = existing_skus
        self.post_payloads = []
        self._next_id = 1000

    def get(self, url, headers=None, params=None, timeout=None):
        products = [{"variants": [{"sku": sku}]} for sku in self._existing_skus]
        return _FakeResponse(json_data={"products": products})

    def post(self, url, headers=None, json=None, timeout=None):
        self.post_payloads.append(json)
        self._next_id += 1
        return _FakeResponse(json_data={"product": {"id": self._next_id}})


def _make_item(sku: str) -> PurchaseListItem:
    product = Product(
        platform="test",
        sku=sku,
        name=f"Product {sku}",
        cost_price=1.0,
        recommended_retail_price=2.0,
        stock_qty=10,
        category="Misc",
    )
    return PurchaseListItem(
        product=product,
        channel="shopify",
        target_sell_price=2.0,
        estimated_margin=1.0,
        margin_rate=0.5,
        demand_score=0.0,
        total_score=0.5,
    )


def test_skips_items_whose_sku_already_exists_in_store(monkeypatch):
    monkeypatch.setenv("SHOPIFY_SHOP", "test-shop.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "fake-token")

    fake_session = _FakeSession(existing_skus={"ALREADY-THERE"})
    monkeypatch.setattr(shopify_exporter, "get_session", lambda: fake_session)

    items = [_make_item("ALREADY-THERE"), _make_item("BRAND-NEW")]

    created = shopify_exporter.push_draft_products(items, channel="shopify")

    assert len(fake_session.post_payloads) == 1
    assert fake_session.post_payloads[0]["product"]["variants"][0]["sku"] == "BRAND-NEW"
    assert len(created) == 1


def test_dry_run_without_credentials(monkeypatch):
    monkeypatch.delenv("SHOPIFY_SHOP", raising=False)
    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)

    created = shopify_exporter.push_draft_products([_make_item("X")], channel="shopify")

    assert created == []
