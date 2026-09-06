import pytest

from purchase_pipeline.config import load_config


def _write_config(tmp_path, content: str) -> str:
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_valid_config_loads_without_error(tmp_path):
    path = _write_config(
        tmp_path,
        """
platform: ownerclan
channels: [shopify]
scoring:
  min_margin_rate: 0.15
  min_stock_qty: 5
  top_n: 10
channel_fees:
  shopify:
    commission_rate: 0.0
    payment_fee_rate: 0.02
""",
    )

    config = load_config(path)

    assert config.platform == "ownerclan"
    assert config.channels == ["shopify"]


def test_empty_channels_rejected(tmp_path):
    path = _write_config(tmp_path, "platform: ownerclan\nchannels: []\n")

    with pytest.raises(ValueError, match="channels"):
        load_config(path)


def test_margin_rate_out_of_range_rejected(tmp_path):
    path = _write_config(
        tmp_path,
        """
platform: ownerclan
channels: [shopify]
scoring:
  min_margin_rate: 1.5
""",
    )

    with pytest.raises(ValueError, match="min_margin_rate"):
        load_config(path)


def test_channel_fee_over_100_percent_rejected(tmp_path):
    path = _write_config(
        tmp_path,
        """
platform: ownerclan
channels: [amazon_nl]
channel_fees:
  amazon_nl:
    commission_rate: 0.8
    payment_fee_rate: 0.5
""",
    )

    with pytest.raises(ValueError, match="commission_rate \\+ payment_fee_rate"):
        load_config(path)


def test_missing_fee_entry_warns_but_does_not_raise(tmp_path, caplog):
    path = _write_config(tmp_path, "platform: ownerclan\nchannels: [amazon_nl]\n")

    with caplog.at_level("WARNING"):
        config = load_config(path)

    assert config.channels == ["amazon_nl"]
    assert any("amazon_nl" in record.message for record in caplog.records)
