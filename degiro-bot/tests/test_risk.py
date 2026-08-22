from src.config import RiskConfig
from src.risk import DailyLossCircuitBreaker, size_order, stop_loss_triggered

RISK = RiskConfig(
    max_position_pct=0.10,
    stop_loss_pct=0.05,
    max_daily_loss_pct=0.03,
    max_order_value=1000,
)


def make_breaker():
    return DailyLossCircuitBreaker(RISK)


def test_buy_sized_within_position_and_order_limits():
    breaker = make_breaker()
    breaker.update(100_000)  # sets starting equity, no drawdown yet
    plan = size_order(
        side="BUY", price=50, portfolio_value=100_000, cash_available=50_000,
        current_position_value=0, risk=RISK, circuit_breaker=breaker,
    )
    assert plan.approved
    # max_position_pct caps budget at 10_000, but max_order_value caps it at 1000
    assert plan.quantity == 20  # 1000 / 50


def test_buy_rejected_when_position_already_at_cap():
    breaker = make_breaker()
    breaker.update(100_000)
    plan = size_order(
        side="BUY", price=50, portfolio_value=100_000, cash_available=50_000,
        current_position_value=10_000, risk=RISK, circuit_breaker=breaker,
    )
    assert not plan.approved


def test_circuit_breaker_trips_on_large_drawdown():
    breaker = make_breaker()
    breaker.update(100_000)
    breaker.update(96_000)  # 4% drawdown > 3% max_daily_loss_pct
    assert breaker.tripped

    plan = size_order(
        side="BUY", price=50, portfolio_value=96_000, cash_available=50_000,
        current_position_value=0, risk=RISK, circuit_breaker=breaker,
    )
    assert not plan.approved
    assert "circuit breaker" in plan.reason


def test_circuit_breaker_resets_next_day():
    breaker = make_breaker()
    breaker.update(100_000)
    breaker.update(96_000)
    assert breaker.tripped

    breaker.reset_for_new_day(96_000)
    assert not breaker.tripped
    assert breaker.starting_equity == 96_000


def test_stop_loss_triggered_past_threshold():
    assert stop_loss_triggered(entry_price=100, current_price=94, risk=RISK)
    assert not stop_loss_triggered(entry_price=100, current_price=96, risk=RISK)
