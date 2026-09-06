"""Historical price data for signal generation.

Kronos uses Yahoo Finance (via `yfinance`) to fetch OHLCV history for
generating trading signals. This is independent from the broker
connection: IBKR is only used for account state and order execution,
while yfinance gives us free, no-auth historical data for European
tickers (e.g. "ASML" -> "ASML.AS" on Euronext Amsterdam).

This keeps the strategy layer testable without any live connection:
tests build small pandas DataFrames by hand instead of hitting the
network.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Default suffix per exchange, for building Yahoo Finance tickers out of
# plain symbols such as "ASML" or "ADYEN".
EXCHANGE_SUFFIX = {
    "AEB": ".AS",  # Euronext Amsterdam
    "EBR": ".BR",  # Euronext Brussels
    "EPA": ".PA",  # Euronext Paris
    "IBIS": ".DE",  # Xetra
    "LSE": ".L",  # London Stock Exchange
}


@dataclass
class PriceBar:
    date: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


def to_yahoo_ticker(symbol: str, exchange: str = "AEB") -> str:
    if "." in symbol:
        return symbol  # already a fully-qualified Yahoo ticker
    suffix = EXCHANGE_SUFFIX.get(exchange.upper(), "")
    return f"{symbol}{suffix}"


def get_price_history(
    symbol: str,
    exchange: str = "AEB",
    period: str = "6mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """Return a DataFrame indexed by date with columns:
    open, high, low, close, volume.

    Raises RuntimeError if yfinance is not installed or no data is
    returned (e.g. bad symbol, no network).
    """
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - exercised only without the dep
        raise RuntimeError(
            "yfinance is required to fetch price history. "
            "Install it with `pip install yfinance`."
        ) from exc

    ticker = to_yahoo_ticker(symbol, exchange)
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if df is None or df.empty:
        raise RuntimeError(f"No price history returned for {ticker}")

    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    return df[["open", "high", "low", "close", "volume"]]
