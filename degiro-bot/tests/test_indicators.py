import pandas as pd

from src.indicators import relative_strength_index, simple_moving_average


def test_simple_moving_average():
    prices = pd.Series([1, 2, 3, 4, 5])
    sma = simple_moving_average(prices, period=3)
    assert pd.isna(sma.iloc[0])
    assert pd.isna(sma.iloc[1])
    assert sma.iloc[2] == 2.0
    assert sma.iloc[4] == 4.0


def test_rsi_all_gains_is_100():
    prices = pd.Series(range(1, 20))  # strictly increasing
    rsi = relative_strength_index(prices, period=14)
    assert rsi.iloc[-1] == 100


def test_rsi_all_losses_is_0():
    prices = pd.Series(range(20, 1, -1))  # strictly decreasing
    rsi = relative_strength_index(prices, period=14)
    assert rsi.iloc[-1] == 0


def test_rsi_flat_prices_is_neutral():
    prices = pd.Series([10] * 20)
    rsi = relative_strength_index(prices, period=14)
    assert rsi.iloc[-1] == 50
