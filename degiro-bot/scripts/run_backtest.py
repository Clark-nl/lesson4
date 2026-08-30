"""Backtest the configured strategy against a buy-and-hold S&P 500 benchmark.

Data sources (in order of preference):
  1. --symbol-csv / --benchmark-csv : local CSV files with "date,close" columns.
  2. --yf-symbol / --yf-benchmark   : ticker symbols fetched via yfinance
     (requires `pip install yfinance` and outbound internet access).

Usage examples:
    python -m scripts.run_backtest --yf-symbol IWDA.AS --yf-benchmark ^GSPC --years 5
    python -m scripts.run_backtest --symbol-csv data/iwda.csv --benchmark-csv data/spx.csv

This does not touch DeGiro or place any orders — it only needs price history.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.backtest import buy_and_hold, run_backtest
from src.config import BASE_DIR, load_strategy_and_risk


def load_csv_series(path: str) -> pd.Series:
    df = pd.read_csv(path, parse_dates=["date"])
    return df.set_index("date")["close"].sort_index()


def load_yf_series(ticker: str, years: int) -> pd.Series:
    try:
        import yfinance as yf
    except ImportError:
        raise SystemExit("yfinance not installed. Run `pip install yfinance` or use --*-csv instead.")

    data = yf.download(ticker, period=f"{years}y", progress=False)
    if data.empty:
        raise SystemExit(
            f"No data returned for '{ticker}'. Check the ticker, your internet connection, "
            f"or use --*-csv with local data instead."
        )
    close = data["Close"]
    if hasattr(close, "columns"):  # yfinance can return a single-column DataFrame
        close = close.iloc[:, 0]
    close.index.name = "date"
    return close


def print_report(name: str, curve: pd.Series) -> None:
    from src.backtest import BacktestResult
    result = BacktestResult(equity_curve=curve, trades=[])
    print(f"{name:>20}: total return {result.total_return_pct:+7.2f}%   "
          f"CAGR {result.cagr_pct:+6.2f}%   max drawdown {result.max_drawdown_pct:6.2f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--symbol-csv", help="CSV with date,close for the traded symbol")
    parser.add_argument("--benchmark-csv", help="CSV with date,close for the S&P 500 benchmark")
    parser.add_argument("--yf-symbol", help="Ticker to fetch via yfinance for the traded symbol")
    parser.add_argument("--yf-benchmark", default="^GSPC", help="Ticker for the benchmark (default: ^GSPC)")
    parser.add_argument("--years", type=int, default=5, help="Years of history to fetch via yfinance")
    parser.add_argument("--initial-cash", type=float, default=10_000.0)
    parser.add_argument("--config", default=str(BASE_DIR / "config.yaml"))
    args = parser.parse_args()

    if args.symbol_csv:
        symbol_prices = load_csv_series(args.symbol_csv)
    elif args.yf_symbol:
        symbol_prices = load_yf_series(args.yf_symbol, args.years)
    else:
        raise SystemExit("Provide either --symbol-csv or --yf-symbol.")

    if args.benchmark_csv:
        benchmark_prices = load_csv_series(args.benchmark_csv)
    else:
        benchmark_prices = load_yf_series(args.yf_benchmark, args.years)

    _, strategy, risk, _ = load_strategy_and_risk(args.config)

    strategy_result = run_backtest(symbol_prices, strategy, risk, initial_cash=args.initial_cash)
    benchmark_curve = buy_and_hold(benchmark_prices, initial_cash=args.initial_cash)

    print(f"\nBacktest period: {symbol_prices.index[0].date()} -> {symbol_prices.index[-1].date()}")
    print(f"Trades executed: {len(strategy_result.trades)}\n")
    print_report("Strategy", strategy_result.equity_curve)
    print_report("S&P 500 buy&hold", benchmark_curve)

    beat = strategy_result.equity_curve.iloc[-1] > benchmark_curve.iloc[-1]
    print(f"\n{'✅ Strategy beat the S&P 500.' if beat else '❌ Strategy did NOT beat the S&P 500.'}")


if __name__ == "__main__":
    main()
