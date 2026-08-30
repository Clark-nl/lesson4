"""Grid-search strategy parameters, then validate the best one out-of-sample.

Optimizing directly on the full history and reporting that result is a classic
overfitting trap — a parameter combo can look great purely because it happens
to fit the noise in that specific period. This script splits the data into a
training period (where the grid search runs) and a held-out test period
(never seen during search), and reports both, so you can see whether the
"winning" parameters actually generalize or just fit the training window.

Usage:
    python -m scripts.optimize_strategy --yf-symbol IWDA.AS --yf-benchmark ^GSPC --years 8
    python -m scripts.optimize_strategy --symbol-csv data/iwda.csv --benchmark-csv data/spx.csv
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backtest import BacktestResult, buy_and_hold, run_backtest
from src.config import BASE_DIR, load_strategy_and_risk
from src.optimize import grid_search, split_train_test
from scripts.run_backtest import load_csv_series, load_yf_series


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--symbol-csv")
    parser.add_argument("--benchmark-csv")
    parser.add_argument("--yf-symbol")
    parser.add_argument("--yf-benchmark", default="^GSPC")
    parser.add_argument("--years", type=int, default=8)
    parser.add_argument("--initial-cash", type=float, default=10_000.0)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--config", default=str(BASE_DIR / "config.yaml"),
                         help="Only the risk section is used; strategy params come from the grid.")
    parser.add_argument("--top", type=int, default=5, help="How many top training results to test out-of-sample")
    args = parser.parse_args()

    if args.symbol_csv:
        prices = load_csv_series(args.symbol_csv)
    elif args.yf_symbol:
        prices = load_yf_series(args.yf_symbol, args.years)
    else:
        raise SystemExit("Provide either --symbol-csv or --yf-symbol.")

    if args.benchmark_csv:
        benchmark_prices = load_csv_series(args.benchmark_csv)
    else:
        benchmark_prices = load_yf_series(args.yf_benchmark, args.years)

    _, _, risk, _ = load_strategy_and_risk(args.config)

    train_prices, test_prices = split_train_test(prices, args.train_fraction)
    train_benchmark, test_benchmark = split_train_test(benchmark_prices, args.train_fraction)

    print(f"Training period: {train_prices.index[0].date()} -> {train_prices.index[-1].date()} "
          f"({len(train_prices)} bars)")
    print(f"Test period:     {test_prices.index[0].date()} -> {test_prices.index[-1].date()} "
          f"({len(test_prices)} bars)\n")

    results = grid_search(
        train_prices, train_benchmark, risk,
        fast_ma_periods=[10, 20, 30, 50],
        slow_ma_periods=[50, 100, 150, 200],
        rsi_periods=[14],
        rsi_buy_below_options=[30, 40, 50, 60, 70, 100],
        rsi_sell_above_options=[0, 30, 40, 50, 60, 70],
        initial_cash=args.initial_cash,
    )

    print(f"Evaluated {len(results)} valid parameter combinations on the training period.\n")
    print(f"{'fast':>5} {'slow':>5} {'buy<':>6} {'sell>':>6} {'trades':>7} "
          f"{'train_return%':>14} {'train_CAGR%':>12}")
    for r in results[: args.top]:
        s = r.strategy
        print(f"{s.fast_ma_period:>5} {s.slow_ma_period:>5} {s.rsi_buy_below:>6} {s.rsi_sell_above:>6} "
              f"{r.num_trades:>7} {r.total_return_pct:>14.2f} {r.cagr_pct:>12.2f}")

    train_benchmark_result = BacktestResult(equity_curve=buy_and_hold(train_benchmark, args.initial_cash), trades=[])
    test_benchmark_result = BacktestResult(equity_curve=buy_and_hold(test_benchmark, args.initial_cash), trades=[])
    print(f"\nBenchmark (train): {train_benchmark_result.total_return_pct:+.2f}%   "
          f"(test): {test_benchmark_result.total_return_pct:+.2f}%")

    print(f"\n--- Out-of-sample validation of top {min(args.top, len(results))} on the held-out test period ---")
    print(f"{'fast':>5} {'slow':>5} {'buy<':>6} {'sell>':>6} {'trades':>7} "
          f"{'test_return%':>13} {'beats bench?':>13}")
    for r in results[: args.top]:
        s = r.strategy
        test_result = run_backtest(test_prices, s, risk, initial_cash=args.initial_cash)
        beats = test_result.total_return_pct > test_benchmark_result.total_return_pct
        print(f"{s.fast_ma_period:>5} {s.slow_ma_period:>5} {s.rsi_buy_below:>6} {s.rsi_sell_above:>6} "
              f"{len(test_result.trades):>7} {test_result.total_return_pct:>13.2f} "
              f"{'YES' if beats else 'no':>13}")

    print("\nOnly trust a parameter set that beats the benchmark on BOTH the training and the "
          "held-out test period — a training-only win is likely overfit to that specific window.")


if __name__ == "__main__":
    main()
