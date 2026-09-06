from purchase_pipeline.platforms.csv_utils import DEFAULT_CSV_COLUMN_MAP, parse_csv_products


def test_skips_malformed_rows_and_keeps_good_ones(caplog):
    csv_text = (
        "sku,name,wholesale_price,retail_price,stock,category\n"
        "GOOD-1,Good Widget,2.5,9.99,10,Misc\n"
        "BAD-1,Bad Widget,N/A,9.99,10,Misc\n"
        "GOOD-2,Another Widget,3.0,12.0,5,Misc\n"
    )

    with caplog.at_level("WARNING"):
        products = parse_csv_products(csv_text, DEFAULT_CSV_COLUMN_MAP, "test")

    assert {p.sku for p in products} == {"GOOD-1", "GOOD-2"}
    assert any("BAD-1" in record.message for record in caplog.records)


def test_all_good_rows_parse_normally():
    csv_text = "sku,name,wholesale_price,retail_price,stock,category\nX,Widget,1,2,3,Misc\n"

    products = parse_csv_products(csv_text, DEFAULT_CSV_COLUMN_MAP, "test")

    assert len(products) == 1
    assert products[0].sku == "X"
