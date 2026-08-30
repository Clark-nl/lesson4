import numpy as np
import pandas as pd

from src.config import StrategyConfig
from src.strategy import Signal, evaluate
from src.vector_strategy import generate_signals

CONFIG = StrategyConfig(
    fast_ma_period=5,
    slow_ma_period=15,
    rsi_period=10,
    rsi_buy_below=50,
    rsi_sell_above=50,
)


def test_vectorized_signals_match_pointwise_evaluate_on_every_bar():
    rng = np.random.default_rng(seed=42)
    steps = rng.normal(loc=0, scale=1.5, size=300)
    prices = pd.Series(100 + np.cumsum(steps))

    vectorized = generate_signals(prices, CONFIG)
    min_len = max(CONFIG.slow_ma_period, CONFIG.rsi_period) + 1

    mismatches = []
    for i in range(min_len, len(prices)):
        window = prices.iloc[: i + 1]
        pointwise = evaluate(window, CONFIG)

        row = vectorized.iloc[i]
        vec_signal = Signal.BUY if row["buy"] else (Signal.SELL if row["sell"] else Signal.HOLD)

        if pointwise.signal != vec_signal:
            mismatches.append((i, pointwise.signal, vec_signal))

    assert not mismatches, f"signal mismatches at bars: {mismatches[:5]} (total {len(mismatches)})"
