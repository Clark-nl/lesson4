import pytest

from kronos.broker.base import AccountSummary, Order, OrderSide
from kronos.config import RiskLimits
from kronos.risk.guardrails import RiskManager, RiskViolation


def make_account(cash=10_000.0, realized=0.0, unrealized=0.0):
    return AccountSummary(
        net_liquidation=cash,
        cash_balance=cash,
        realized_pnl_today=realized,
        unrealized_pnl_today=unrealized,
    )


def test_order_within_limits_passes():
    rm = RiskManager(RiskLimits(max_order_value_eur=1000, max_daily_loss_eur=250,
                                 max_position_value_eur=5000, max_orders_per_day=10))
    order = Order(symbol="ASML", side=OrderSide.BUY, quantity=1)
    rm.validate_order(order, reference_price=500.0, account=make_account())


def test_order_over_per_order_cap_rejected():
    rm = RiskManager(RiskLimits(max_order_value_eur=100))
    order = Order(symbol="ASML", side=OrderSide.BUY, quantity=1)
    with pytest.raises(RiskViolation, match="per-order limit"):
        rm.validate_order(order, reference_price=500.0, account=make_account())


def test_daily_loss_limit_blocks_new_orders():
    rm = RiskManager(RiskLimits(max_order_value_eur=1000, max_daily_loss_eur=200))
    order = Order(symbol="ASML", side=OrderSide.BUY, quantity=1)
    account = make_account(realized=-150.0, unrealized=-60.0)  # -210 total
    with pytest.raises(RiskViolation, match="Daily loss limit"):
        rm.validate_order(order, reference_price=100.0, account=account)


def test_max_orders_per_day_enforced():
    rm = RiskManager(RiskLimits(max_order_value_eur=1000, max_orders_per_day=2))
    order = Order(symbol="ASML", side=OrderSide.BUY, quantity=1)
    rm.validate_order(order, reference_price=10.0, account=make_account())
    rm.record_order_placed()
    rm.validate_order(order, reference_price=10.0, account=make_account())
    rm.record_order_placed()
    with pytest.raises(RiskViolation, match="Daily order count limit"):
        rm.validate_order(order, reference_price=10.0, account=make_account())


def test_position_cap_blocks_buy_that_would_exceed_it():
    rm = RiskManager(RiskLimits(max_order_value_eur=1000, max_position_value_eur=1500))
    order = Order(symbol="ASML", side=OrderSide.BUY, quantity=10)
    with pytest.raises(RiskViolation, match="max position value"):
        rm.validate_order(
            order, reference_price=100.0, account=make_account(),
            current_position_value=600.0,  # 600 + 1000 = 1600 > 1500
        )


def test_insufficient_cash_blocks_buy():
    rm = RiskManager(RiskLimits(max_order_value_eur=1000))
    order = Order(symbol="ASML", side=OrderSide.BUY, quantity=5)
    with pytest.raises(RiskViolation, match="Insufficient cash"):
        rm.validate_order(order, reference_price=100.0, account=make_account(cash=100.0))


def test_sell_not_blocked_by_cash_check():
    rm = RiskManager(RiskLimits(max_order_value_eur=1000))
    order = Order(symbol="ASML", side=OrderSide.SELL, quantity=5)
    # Should not raise even though cash is low -- selling raises cash, doesn't need it.
    rm.validate_order(order, reference_price=100.0, account=make_account(cash=0.0))
