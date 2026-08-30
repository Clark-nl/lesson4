"""Vectorized version of strategy.evaluate(), for backtesting many days at once.

Kept as a separate module (rather than vectorizing strategy.py itself) so the
live bot keeps using the simple, easy-to-read single-point evaluate(); the
two are cross-checked in tests/test_vector_strategy.py to make sure they
agree on every bar.
"""

import pandas as pd

from .config import StrategyConfig
from .indicators import relative_strength_index, simple_moving_average


def generate_signals(prices: pd.Series, config: StrategyConfig) -> pd.DataFrame:
    fast = simple_moving_average(prices, config.fast_ma_period)
    slow = simple_moving_average(prices, config.slow_ma_period)
    rsi = relative_strength_index(prices, config.rsi_period)

    crossed_up = (fast.shift(1) <= slow.shift(1)) & (fast > slow)
    crossed_down = (fast.shift(1) >= slow.shift(1)) & (fast < slow)

    buy = crossed_up & (rsi < config.rsi_buy_below)
    sell = crossed_down & (rsi > config.rsi_sell_above)

    return pd.DataFrame({"price": prices, "fast_ma": fast, "slow_ma": slow, "rsi": rsi,
                          "buy": buy.fillna(False), "sell": sell.fillna(False)})
