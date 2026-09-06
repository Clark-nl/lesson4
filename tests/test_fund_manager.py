import numpy as np
import pandas as pd
import pytest

from kronos.agent.fund_manager import Kronos
from kronos.approval.human_approval import CallbackApprovalGate
from kronos.broker.fake import FakeBroker
from kronos.config import IBKRSettings, KronosConfig, RiskLimits


def uptrend_history_fn(symbol: str, exchange: str) -> pd.DataFrame:
    closes = list(np.linspace(100, 140, 60))
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    return pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes,
         "volume": [1_000_000] * 60},
        index=dates,
    )


def flat_history_fn(symbol: str, exchange: str) -> pd.DataFrame:
    closes = [100.0] * 60
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    return pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes,
         "volume": [1_000_000] * 60},
        index=dates,
    )


def make_config(**overrides) -> KronosConfig:
    defaults = dict(
        live_trading=False,
        require_human_approval=True,
        watchlist=["ASML"],
        risk=RiskLimits(max_order_value_eur=1000, max_daily_loss_eur=250,
                         max_position_value_eur=5000, max_orders_per_day=10),
        ibkr=IBKRSettings(),
    )
    defaults.update(overrides)
    return KronosConfig(**defaults)


def test_dry_run_executes_simulated_buy():
    config = make_config(live_trading=False)
    broker = FakeBroker(starting_cash=10_000, prices={"ASML": 140.0})
    kronos = Kronos(config, broker=broker, price_history_fn=uptrend_history_fn)

    result = kronos.run_cycle("ASML")

    assert result.order_result is not None
    assert result.order_result.status == "SIMULATED"
    assert len(broker.orders) == 1


def test_hold_signal_produces_no_order():
    config = make_config()
    broker = FakeBroker(starting_cash=10_000, prices={"ASML": 100.0})
    kronos = Kronos(config, broker=broker, price_history_fn=flat_history_fn)

    result = kronos.run_cycle("ASML")

    assert result.order is None
    assert result.skipped_reason == "HOLD signal, no order generated"
    assert len(broker.orders) == 0


def test_live_trading_denied_by_human_places_no_order():
    config = make_config(live_trading=True, require_human_approval=True)
    broker = FakeBroker(starting_cash=10_000, prices={"ASML": 140.0})
    gate = CallbackApprovalGate(lambda order, value, account: False)
    kronos = Kronos(config, broker=broker, approval_gate=gate, price_history_fn=uptrend_history_fn)

    result = kronos.run_cycle("ASML")

    assert result.skipped_reason == "not approved by human"
    assert len(broker.orders) == 0


def test_live_trading_approved_by_human_places_order():
    config = make_config(live_trading=True, require_human_approval=True)
    broker = FakeBroker(starting_cash=10_000, prices={"ASML": 140.0})
    gate = CallbackApprovalGate(lambda order, value, account: True)
    kronos = Kronos(config, broker=broker, approval_gate=gate, price_history_fn=uptrend_history_fn)

    result = kronos.run_cycle("ASML")

    assert result.order_result is not None
    assert len(broker.orders) == 1


def test_live_trading_without_human_approval_refused_at_construction():
    config = make_config(live_trading=True, require_human_approval=False)
    with pytest.raises(ValueError, match="require_human_approval"):
        Kronos(config, broker=FakeBroker())


def test_risk_violation_blocks_order():
    config = make_config(risk=RiskLimits(max_order_value_eur=10))  # too small to buy anything
    broker = FakeBroker(starting_cash=10_000, prices={"ASML": 140.0})
    kronos = Kronos(config, broker=broker, price_history_fn=uptrend_history_fn)

    result = kronos.run_cycle("ASML")

    assert result.order_result is None
    assert len(broker.orders) == 0


def test_config_from_env_and_file_rejects_live_without_approval(monkeypatch):
    monkeypatch.setenv("KRONOS_LIVE_TRADING", "true")
    monkeypatch.setenv("KRONOS_REQUIRE_APPROVAL", "false")
    with pytest.raises(ValueError, match="require_human_approval"):
        KronosConfig.from_env_and_file(None)


def test_config_defaults_to_dry_run(monkeypatch):
    monkeypatch.delenv("KRONOS_LIVE_TRADING", raising=False)
    config = KronosConfig.from_env_and_file(None)
    assert config.live_trading is False
