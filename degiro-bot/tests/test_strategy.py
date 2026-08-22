import pandas as pd

from src.config import StrategyConfig
from src.strategy import Signal, evaluate

CONFIG = StrategyConfig(
    fast_ma_period=3,
    slow_ma_period=5,
    rsi_period=5,
    rsi_buy_below=60,
    rsi_sell_above=40,
)


def test_hold_with_insufficient_history():
    prices = pd.Series([10, 11, 12])
    result = evaluate(prices, CONFIG)
    assert result.signal == Signal.HOLD
    assert "insufficient" in result.reason


def test_golden_cross_triggers_buy():
    # Prices dip then recover so the fast MA crosses above the slow MA
    # on the final bar, while RSI stays below the buy threshold.
    prices = pd.Series([20, 18, 16, 14, 12, 11, 12, 14, 17])
    result = evaluate(prices, CONFIG)
    assert result.signal == Signal.BUY


def test_death_cross_triggers_sell():
    # Mirror image: prices climb then drop so the fast MA crosses below
    # the slow MA on the final bar, while RSI stays above the sell threshold.
    prices = pd.Series([10, 12, 14, 16, 18, 19, 18, 16, 13])
    result = evaluate(prices, CONFIG)
    assert result.signal == Signal.SELL


def test_flat_prices_hold():
    prices = pd.Series([10] * 10)
    result = evaluate(prices, CONFIG)
    assert result.signal == Signal.HOLD
