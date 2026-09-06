import numpy as np
import pandas as pd

from kronos.strategy.base import Action
from kronos.strategy.vibe import VibeStrategy


def make_price_history(closes, volumes=None) -> pd.DataFrame:
    n = len(closes)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    volumes = volumes or [1_000_000] * n
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": volumes,
        },
        index=dates,
    )


def test_uptrend_produces_buy_signal():
    closes = list(np.linspace(100, 140, 60))  # steady uptrend
    history = make_price_history(closes)
    strategy = VibeStrategy(short_window=10, long_window=50)
    signal = strategy.generate_signal("ASML", history)
    assert signal.action == Action.BUY
    assert signal.confidence > 0


def test_downtrend_produces_sell_signal():
    closes = list(np.linspace(140, 100, 60))  # steady downtrend
    history = make_price_history(closes)
    strategy = VibeStrategy(short_window=10, long_window=50)
    signal = strategy.generate_signal("ASML", history)
    assert signal.action == Action.SELL
    assert signal.confidence > 0


def test_flat_market_produces_hold_signal():
    closes = [100.0] * 60
    history = make_price_history(closes)
    strategy = VibeStrategy(short_window=10, long_window=50)
    signal = strategy.generate_signal("ASML", history)
    assert signal.action == Action.HOLD


def test_empty_history_holds_safely():
    strategy = VibeStrategy()
    signal = strategy.generate_signal("ASML", pd.DataFrame())
    assert signal.action == Action.HOLD
    assert signal.confidence == 0.0


def test_signal_reasons_are_populated():
    closes = list(np.linspace(100, 140, 60))
    history = make_price_history(closes)
    strategy = VibeStrategy()
    signal = strategy.generate_signal("ASML", history)
    assert len(signal.reasons) >= 3
