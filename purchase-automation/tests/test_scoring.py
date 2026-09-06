from purchase_pipeline.config import PipelineConfig, ScoringConfig
from purchase_pipeline.models import Product
from purchase_pipeline.scoring import score_products


def make_config(**overrides) -> PipelineConfig:
    scoring = ScoringConfig(
        min_margin_rate=overrides.pop("min_margin_rate", 0.15),
        min_stock_qty=overrides.pop("min_stock_qty", 5),
        top_n=overrides.pop("top_n", 50),
        margin_weight=overrides.pop("margin_weight", 0.6),
        demand_weight=overrides.pop("demand_weight", 0.4),
    )
    return PipelineConfig(
        platform="ownerclan",
        channels=overrides.pop("channels", ["shopify"]),
        scoring=scoring,
        channel_fees=overrides.pop(
            "channel_fees",
            {"shopify": {"commission_rate": 0.0, "payment_fee_rate": 0.0, "fixed_fee": 0.0}},
        ),
    )


def make_product(**overrides) -> Product:
    defaults = dict(
        platform="ownerclan",
        sku="SKU-1",
        name="Test Product",
        cost_price=1000.0,
        recommended_retail_price=2000.0,
        stock_qty=50,
        category="misc",
        sold_last_30d=10,
    )
    defaults.update(overrides)
    return Product(**defaults)


def test_low_stock_products_are_filtered_out():
    config = make_config(min_stock_qty=10)
    products = [make_product(sku="LOW", stock_qty=1), make_product(sku="OK", stock_qty=50)]

    items = score_products(products, config)

    assert [item.product.sku for item in items] == ["OK"]


def test_low_margin_products_are_filtered_out():
    config = make_config(min_margin_rate=0.4)
    # margin_rate = (2000 - 1000) / 2000 = 0.5 -> passes
    high_margin = make_product(sku="HIGH", cost_price=1000, recommended_retail_price=2000)
    # margin_rate = (2000 - 1900) / 2000 = 0.05 -> filtered
    low_margin = make_product(sku="LOW", cost_price=1900, recommended_retail_price=2000)

    items = score_products([high_margin, low_margin], config)

    assert [item.product.sku for item in items] == ["HIGH"]


def test_top_n_limits_result_count():
    config = make_config(top_n=2, min_stock_qty=0, min_margin_rate=0.0)
    products = [make_product(sku=f"SKU-{i}", sold_last_30d=i) for i in range(5)]

    items = score_products(products, config)

    assert len(items) == 2


def test_results_sorted_by_total_score_descending():
    config = make_config(min_stock_qty=0, min_margin_rate=0.0)
    products = [
        make_product(sku="LOW-DEMAND", sold_last_30d=1),
        make_product(sku="HIGH-DEMAND", sold_last_30d=100),
    ]

    items = score_products(products, config)

    assert [item.product.sku for item in items] == ["HIGH-DEMAND", "LOW-DEMAND"]
    assert items[0].total_score >= items[1].total_score


def test_one_row_per_configured_channel():
    config = make_config(
        channels=["shopify", "coupang"],
        min_stock_qty=0,
        min_margin_rate=0.0,
        channel_fees={
            "shopify": {"commission_rate": 0.0, "payment_fee_rate": 0.0, "fixed_fee": 0.0},
            "coupang": {"commission_rate": 0.1, "payment_fee_rate": 0.0, "fixed_fee": 0.0},
        },
    )
    products = [make_product(sku="MULTI")]

    items = score_products(products, config)

    assert sorted(item.channel for item in items) == ["coupang", "shopify"]
