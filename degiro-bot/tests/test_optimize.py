import numpy as np
import pandas as pd

from src.config import RiskConfig
from src.optimize import grid_search, split_train_test

RISK = RiskConfig(
    max_position_pct=1.0,
    stop_loss_pct=0.20,
    max_daily_loss_pct=0.50,
    max_order_value=1_000_000,
)


def dated(values, start="2020-01-01"):
    index = pd.date_range(start=start, periods=len(values), freq="D")
    return pd.Series(values, index=index)


def test_split_train_test_respects_fraction_and_order():
    prices = dated(list(range(100)))
    train, test = split_train_test(prices, train_fraction=0.7)
    assert len(train) == 70
    assert len(test) == 30
    assert train.index[-1] < test.index[0]


def test_grid_search_skips_invalid_fast_ge_slow_combos():
    rng = np.random.default_rng(1)
    prices = dated(100 + np.cumsum(rng.normal(0, 1, 200)))
    benchmark = dated(100 + np.cumsum(rng.normal(0.05, 0.5, 200)))

    results = grid_search(
        prices, benchmark, RISK,
        fast_ma_periods=[10, 20],
        slow_ma_periods=[10, 20],  # fast==slow combos must be skipped
        rsi_periods=[14],
        rsi_buy_below_options=[100],  # no filter -> trades happen
        rsi_sell_above_options=[0],
    )
    # only (10,20) is valid; (10,10),(20,10),(20,20) are skipped
    assert len(results) == 1
    assert results[0].strategy.fast_ma_period == 10
    assert results[0].strategy.slow_ma_period == 20


def test_grid_search_sorted_best_first_and_flags_beating_benchmark():
    rng = np.random.default_rng(3)
    prices = dated(100 + np.cumsum(rng.normal(0.1, 1, 300)))
    benchmark = dated(100 + np.cumsum(rng.normal(0.02, 0.3, 300)))

    results = grid_search(
        prices, benchmark, RISK,
        fast_ma_periods=[5, 10],
        slow_ma_periods=[20, 40],
        rsi_periods=[14],
        rsi_buy_below_options=[50, 100],
        rsi_sell_above_options=[0, 50],
    )
    assert len(results) > 1
    returns = [r.total_return_pct for r in results]
    assert returns == sorted(returns, reverse=True)
    # at least one config should be flagged consistently with its own return
    # vs the benchmark buy-and-hold return computed independently
    from src.backtest import BacktestResult, buy_and_hold
    bench_return = BacktestResult(equity_curve=buy_and_hold(benchmark, 10_000), trades=[]).total_return_pct
    for r in results:
        assert r.beat_benchmark == (r.total_return_pct > bench_return)


def test_no_filter_config_trades_more_than_strict_filter():
    rng = np.random.default_rng(5)
    prices = dated(100 + np.cumsum(rng.normal(0, 1.5, 400)))
    benchmark = dated(100 + np.cumsum(rng.normal(0.02, 0.5, 400)))

    results = grid_search(
        prices, benchmark, RISK,
        fast_ma_periods=[10],
        slow_ma_periods=[30],
        rsi_periods=[14],
        rsi_buy_below_options=[30, 100],  # 30 = strict oversold filter, 100 = no filter
        rsi_sell_above_options=[70, 0],   # 70 = strict overbought filter, 0 = no filter
    )
    by_buy_below = {r.strategy.rsi_buy_below: r for r in results}
    assert by_buy_below[100].num_trades >= by_buy_below[30].num_trades
