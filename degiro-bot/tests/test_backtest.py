import pandas as pd
import pytest

from src.backtest import BacktestResult, buy_and_hold, run_backtest
from src.config import RiskConfig, StrategyConfig

STRATEGY = StrategyConfig(
    fast_ma_period=3,
    slow_ma_period=5,
    rsi_period=5,
    rsi_buy_below=60,
    rsi_sell_above=40,
)
RISK = RiskConfig(
    max_position_pct=1.0,
    stop_loss_pct=0.20,
    max_daily_loss_pct=0.50,
    max_order_value=1_000_000,
)


def dated(values, start="2024-01-01"):
    index = pd.date_range(start=start, periods=len(values), freq="D")
    return pd.Series(values, index=index)


def test_buy_and_hold_tracks_price_return_exactly():
    prices = dated([100, 110, 121])
    curve = buy_and_hold(prices, initial_cash=1000)
    assert curve.iloc[0] == pytest.approx(1000)
    assert curve.iloc[-1] == pytest.approx(1210)  # +10% then +10% = +21%


def test_flat_prices_produce_no_trades_and_flat_equity():
    prices = dated([100] * 10)
    result = run_backtest(prices, STRATEGY, RISK, initial_cash=1000)
    assert result.trades == []
    assert (result.equity_curve == 1000).all()


def test_golden_cross_executes_a_buy_and_moves_equity_with_price():
    # Same shape as test_strategy.test_golden_cross_triggers_buy: dip then
    # recover, triggering a BUY on the last bar.
    prices = dated([20, 18, 16, 14, 12, 11, 12, 14, 17])
    result = run_backtest(prices, STRATEGY, RISK, initial_cash=1000)

    assert len(result.trades) == 1
    buy = result.trades[0]
    assert buy.side == "BUY"
    assert buy.price == 17
    assert buy.quantity == 1000 // 17

    # Equity on the buy bar = leftover cash + position value at that price.
    expected_equity = (1000 - buy.quantity * 17) + buy.quantity * 17
    assert result.equity_curve.iloc[-1] == pytest.approx(expected_equity)
    assert expected_equity == pytest.approx(1000)  # no price move yet on the fill bar itself


def test_stop_loss_exits_full_position_after_a_big_drop():
    # Trigger a buy on the golden cross, then crash the price past stop_loss_pct.
    prices = dated([20, 18, 16, 14, 12, 11, 12, 14, 17, 13])  # 17 -> 13 is a 23.5% drop
    result = run_backtest(prices, STRATEGY, RISK, initial_cash=1000)

    sides = [t.side for t in result.trades]
    assert sides == ["BUY", "SELL"]
    assert result.trades[1].reason == "stop-loss"
    # Fully exited: last equity point should be all cash, no leftover position value.
    buy_qty = result.trades[0].quantity
    sell_qty = result.trades[1].quantity
    assert sell_qty == buy_qty


def test_metrics_on_a_known_equity_curve():
    curve = dated([100, 200, 50, 150])
    result = BacktestResult(equity_curve=curve, trades=[])
    assert result.total_return_pct == pytest.approx(50.0)  # 100 -> 150
    assert result.max_drawdown_pct == pytest.approx(-75.0)  # 200 -> 50
