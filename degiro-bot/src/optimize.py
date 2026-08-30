from dataclasses import dataclass
from itertools import product

import pandas as pd

from .backtest import BacktestResult, buy_and_hold, run_backtest
from .config import RiskConfig, StrategyConfig


@dataclass
class GridResult:
    strategy: StrategyConfig
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    num_trades: int
    beat_benchmark: bool


def grid_search(prices: pd.Series, benchmark_prices: pd.Series, risk: RiskConfig,
                 fast_ma_periods: list[int], slow_ma_periods: list[int],
                 rsi_periods: list[int], rsi_buy_below_options: list[float],
                 rsi_sell_above_options: list[float],
                 initial_cash: float = 10_000.0) -> list[GridResult]:
    """Backtest every valid (fast < slow) combination in the grid and return
    results sorted by total return, best first."""
    benchmark_return_pct = BacktestResult(equity_curve=buy_and_hold(benchmark_prices, initial_cash),
                                           trades=[]).total_return_pct

    results = []
    combos = product(fast_ma_periods, slow_ma_periods, rsi_periods,
                      rsi_buy_below_options, rsi_sell_above_options)
    for fast, slow, rsi_period, buy_below, sell_above in combos:
        if fast >= slow:
            continue
        strategy = StrategyConfig(
            fast_ma_period=fast,
            slow_ma_period=slow,
            rsi_period=rsi_period,
            rsi_buy_below=buy_below,
            rsi_sell_above=sell_above,
        )
        result = run_backtest(prices, strategy, risk, initial_cash=initial_cash)
        results.append(GridResult(
            strategy=strategy,
            total_return_pct=result.total_return_pct,
            cagr_pct=result.cagr_pct,
            max_drawdown_pct=result.max_drawdown_pct,
            num_trades=len(result.trades),
            beat_benchmark=result.total_return_pct > benchmark_return_pct,
        ))

    results.sort(key=lambda r: r.total_return_pct, reverse=True)
    return results


def split_train_test(prices: pd.Series, train_fraction: float = 0.7) -> tuple[pd.Series, pd.Series]:
    split_idx = int(len(prices) * train_fraction)
    return prices.iloc[:split_idx], prices.iloc[split_idx:]
