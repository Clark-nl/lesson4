from purchase_pipeline.platforms.csv_import import CSVImportPlatform


def test_mock_mode_reads_fixture_csv():
    platform = CSVImportPlatform(mock=True)

    products = platform.fetch_catalog()

    assert len(products) == 6
    first = next(p for p in products if p.sku == "CI-002")
    assert first.name == "Red Light Therapy Mask"
    assert first.cost_price == 14.00
    assert first.recommended_retail_price == 49.95
    assert first.stock_qty == 80
    assert first.category == "Beauty & Wellness"


def test_defaults_to_mock_mode_without_source(monkeypatch):
    monkeypatch.delenv("CSV_IMPORT_SOURCE", raising=False)
    monkeypatch.delenv("CSV_IMPORT_MOCK", raising=False)

    platform = CSVImportPlatform()

    assert platform.mock is True
    assert len(platform.fetch_catalog()) == 6


def test_reads_from_local_file_path(tmp_path):
    csv_path = tmp_path / "my_shortlist.csv"
    csv_path.write_text(
        "sku,name,wholesale_price,retail_price,stock,category\n"
        "LOCAL-1,Local Widget,2.0,6.0,20,Misc\n",
        encoding="utf-8",
    )

    platform = CSVImportPlatform(source=str(csv_path))

    products = platform.fetch_catalog()

    assert len(products) == 1
    assert products[0].sku == "LOCAL-1"
    assert products[0].cost_price == 2.0
