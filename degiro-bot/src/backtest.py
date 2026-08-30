from dataclasses import dataclass

import pandas as pd

from .config import RiskConfig, StrategyConfig
from .risk import DailyLossCircuitBreaker, size_order, stop_loss_triggered
from .vector_strategy import generate_signals


@dataclass
class Trade:
    date: object
    side: str
    price: float
    quantity: int
    reason: str


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[Trade]

    @property
    def total_return_pct(self) -> float:
        return (self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1) * 100

    @property
    def cagr_pct(self) -> float:
        days = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days
        years = days / 365.25
        if years <= 0:
            return 0.0
        return ((self.equity_curve.iloc[-1] / self.equity_curve.iloc[0]) ** (1 / years) - 1) * 100

    @property
    def max_drawdown_pct(self) -> float:
        running_max = self.equity_curve.cummax()
        drawdown = (self.equity_curve - running_max) / running_max
        return drawdown.min() * 100


def run_backtest(prices: pd.Series, strategy: StrategyConfig, risk: RiskConfig,
                  initial_cash: float = 10_000.0) -> BacktestResult:
    """Single-symbol backtest. Reuses the exact same size_order/stop_loss_triggered
    logic as the live bot, so backtested behavior matches what the bot would do."""
    signals = generate_signals(prices, strategy)

    cash = initial_cash
    quantity_held = 0
    entry_price: float | None = None
    breaker = DailyLossCircuitBreaker(risk)
    equity_points = []
    trades: list[Trade] = []

    for ts, row in signals.iterrows():
        price = float(row["price"])
        position_value = quantity_held * price
        equity = cash + position_value
        breaker.update(equity)

        if quantity_held > 0 and entry_price and stop_loss_triggered(entry_price, price, risk):
            plan = size_order(side="SELL", price=price, portfolio_value=equity, cash_available=cash,
                               current_position_value=position_value, risk=risk, circuit_breaker=breaker,
                               held_quantity=quantity_held)
            if plan.approved:
                cash += plan.quantity * price
                trades.append(Trade(ts, "SELL", price, plan.quantity, "stop-loss"))
                quantity_held -= plan.quantity
                entry_price = None
        elif row["buy"] and quantity_held == 0:
            plan = size_order(side="BUY", price=price, portfolio_value=equity, cash_available=cash,
                               current_position_value=position_value, risk=risk, circuit_breaker=breaker)
            if plan.approved:
                cash -= plan.quantity * price
                trades.append(Trade(ts, "BUY", price, plan.quantity, "golden cross + RSI"))
                quantity_held += plan.quantity
                entry_price = price
        elif row["sell"] and quantity_held > 0:
            plan = size_order(side="SELL", price=price, portfolio_value=equity, cash_available=cash,
                               current_position_value=position_value, risk=risk, circuit_breaker=breaker,
                               held_quantity=quantity_held)
            if plan.approved:
                cash += plan.quantity * price
                trades.append(Trade(ts, "SELL", price, plan.quantity, "death cross + RSI"))
                quantity_held -= plan.quantity
                entry_price = None

        equity_points.append((ts, cash + quantity_held * price))

    equity_curve = pd.Series({ts: eq for ts, eq in equity_points})
    return BacktestResult(equity_curve=equity_curve, trades=trades)


def buy_and_hold(prices: pd.Series, initial_cash: float = 10_000.0) -> pd.Series:
    shares = initial_cash / prices.iloc[0]
    return prices * shares
