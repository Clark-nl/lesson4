import logging
import time
from datetime import date

import schedule

from .config import Config, load_config
from .degiro_client import DegiroClient
from .risk import DailyLossCircuitBreaker, size_order, stop_loss_triggered
from .strategy import Signal, evaluate

logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self, config: Config, client: DegiroClient):
        self.config = config
        self.client = client
        self.circuit_breaker = DailyLossCircuitBreaker(config.risk)
        self.entry_prices: dict[str, float] = {}
        self._current_day = date.today()

    def run_once(self) -> None:
        if date.today() != self._current_day:
            self._current_day = date.today()
            self.circuit_breaker.reset_for_new_day(self.client.get_portfolio_value())

        portfolio_value = self.client.get_portfolio_value()
        self.circuit_breaker.update(portfolio_value)

        if self.circuit_breaker.tripped:
            logger.warning("Circuit breaker tripped; skipping this cycle for all symbols.")
            return

        cash_available = self.client.get_cash_available()

        for symbol in self.config.symbols:
            self._evaluate_symbol(symbol, portfolio_value, cash_available)

    def _evaluate_symbol(self, symbol, portfolio_value: float, cash_available: float) -> None:
        prices = self.client.get_price_history(symbol.product_id)
        if prices.empty:
            logger.warning("No price history for %s, skipping", symbol.name)
            return

        current_price = float(prices.iloc[-1])
        position_value = self.client.get_position_value(symbol.product_id)

        entry_price = self.entry_prices.get(symbol.product_id)
        if entry_price and position_value > 0 and stop_loss_triggered(entry_price, current_price, self.config.risk):
            self._submit(symbol, "SELL", current_price, portfolio_value, cash_available, position_value,
                         reason="stop-loss triggered")
            self.entry_prices.pop(symbol.product_id, None)
            return

        result = evaluate(prices, self.config.strategy)
        logger.info("%s: signal=%s fast_ma=%.2f slow_ma=%.2f rsi=%.1f (%s)",
                    symbol.name, result.signal, result.fast_ma, result.slow_ma, result.rsi, result.reason)

        if result.signal == Signal.HOLD:
            return

        side = result.signal.value
        self._submit(symbol, side, current_price, portfolio_value, cash_available, position_value,
                     reason=result.reason)
        if side == "BUY":
            self.entry_prices[symbol.product_id] = current_price

    def _submit(self, symbol, side: str, price: float, portfolio_value: float,
                cash_available: float, position_value: float, *, reason: str) -> None:
        plan = size_order(
            side=side,
            price=price,
            portfolio_value=portfolio_value,
            cash_available=cash_available,
            current_position_value=position_value,
            risk=self.config.risk,
            circuit_breaker=self.circuit_breaker,
        )
        if not plan.approved:
            logger.info("%s %s rejected by risk manager: %s", side, symbol.name, plan.reason)
            return

        if not self.config.credentials.risk_confirmed:
            logger.warning(
                "I_UNDERSTAND_THE_RISK is not set to true in .env — order NOT sent. "
                "Would have %s %s x%d (%s)", side, symbol.name, plan.quantity, reason,
            )
            return

        order_id = self.client.place_order(product_id=symbol.product_id, side=side, quantity=plan.quantity)
        logger.info("Order submitted: %s %s x%d -> order_id=%s (%s)",
                    side, symbol.name, plan.quantity, order_id, reason)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = load_config()
    client = DegiroClient(config.credentials)
    client.connect()

    bot = TradingBot(config, client)
    bot.run_once()

    schedule.every(config.interval_minutes).minutes.do(bot.run_once)
    logger.info("Bot scheduled to run every %d minutes. Press Ctrl+C to stop.", config.interval_minutes)
    while True:
        schedule.run_pending()
        time.sleep(5)


if __name__ == "__main__":
    main()
