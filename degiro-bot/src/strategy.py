from dataclasses import dataclass
from enum import Enum

import pandas as pd

from .config import StrategyConfig
from .indicators import relative_strength_index, simple_moving_average


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class SignalResult:
    signal: Signal
    fast_ma: float
    slow_ma: float
    rsi: float
    reason: str


def evaluate(prices: pd.Series, config: StrategyConfig) -> SignalResult:
    """Moving-average crossover, filtered by RSI.

    BUY:  fast MA crosses above slow MA AND RSI is below rsi_buy_below.
    SELL: fast MA crosses below slow MA AND RSI is above rsi_sell_above.
    Otherwise HOLD.
    """
    min_len = max(config.slow_ma_period, config.rsi_period) + 1
    if len(prices) < min_len:
        return SignalResult(Signal.HOLD, float("nan"), float("nan"), float("nan"),
                             f"insufficient price history ({len(prices)} < {min_len})")

    fast = simple_moving_average(prices, config.fast_ma_period)
    slow = simple_moving_average(prices, config.slow_ma_period)
    rsi = relative_strength_index(prices, config.rsi_period)

    fast_now, fast_prev = fast.iloc[-1], fast.iloc[-2]
    slow_now, slow_prev = slow.iloc[-1], slow.iloc[-2]
    rsi_now = rsi.iloc[-1]

    crossed_up = fast_prev <= slow_prev and fast_now > slow_now
    crossed_down = fast_prev >= slow_prev and fast_now < slow_now

    if crossed_up and rsi_now < config.rsi_buy_below:
        return SignalResult(Signal.BUY, fast_now, slow_now, rsi_now,
                             f"golden cross + RSI {rsi_now:.1f} < {config.rsi_buy_below}")

    if crossed_down and rsi_now > config.rsi_sell_above:
        return SignalResult(Signal.SELL, fast_now, slow_now, rsi_now,
                             f"death cross + RSI {rsi_now:.1f} > {config.rsi_sell_above}")

    return SignalResult(Signal.HOLD, fast_now, slow_now, rsi_now, "no crossover with RSI confirmation")
