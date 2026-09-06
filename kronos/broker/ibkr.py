"""Interactive Brokers implementation of the Broker interface.

Uses `ib_insync` to talk to a locally running TWS or IB Gateway. This
module does nothing "magic": it is a thin, explicit translation layer
between Kronos' broker-agnostic Order/Position/AccountSummary types and
ib_insync's Contract/Trade/AccountValue types.

Requirements to actually use this against IBKR:
  - TWS or IB Gateway running and logged in on the machine Kronos runs on
    (or reachable over the network), with the API enabled
    (Configuration > API > Settings > Enable ActiveX and Socket Clients).
  - Paper trading account for anything other than deliberate live use
    (default port 7497 = TWS paper, 7496 = TWS live, 4002 = Gateway
    paper, 4001 = Gateway live).
  - `pip install ib_insync`.
"""
from __future__ import annotations

import logging

from kronos.broker.base import AccountSummary, Broker, Order, OrderResult, Position
from kronos.config import IBKRSettings

logger = logging.getLogger("kronos.broker.ibkr")


class IBKRBroker(Broker):
    def __init__(self, settings: IBKRSettings) -> None:
        self.settings = settings
        self._ib = None  # lazily imported ib_insync.IB instance

    def connect(self) -> None:
        try:
            from ib_insync import IB
        except ImportError as exc:  # pragma: no cover - exercised only without the dep
            raise RuntimeError(
                "ib_insync is required to connect to Interactive Brokers. "
                "Install it with `pip install ib_insync`, and make sure "
                "TWS or IB Gateway is running with the API enabled."
            ) from exc

        self._ib = IB()
        logger.info(
            "Connecting to IBKR at %s:%s (clientId=%s)",
            self.settings.host,
            self.settings.port,
            self.settings.client_id,
        )
        self._ib.connect(
            self.settings.host,
            self.settings.port,
            clientId=self.settings.client_id,
        )

    def disconnect(self) -> None:
        if self._ib is not None:
            self._ib.disconnect()
            self._ib = None

    def _require_connection(self):
        if self._ib is None:
            raise RuntimeError("IBKRBroker is not connected. Call connect() first.")
        return self._ib

    def _make_contract(self, symbol: str, exchange: str | None, currency: str | None):
        from ib_insync import Stock

        return Stock(
            symbol,
            exchange or self.settings.exchange,
            currency or self.settings.currency,
        )

    def get_account_summary(self) -> AccountSummary:
        ib = self._require_connection()
        values = ib.accountSummary(self.settings.account or "")
        by_tag = {v.tag: v for v in values}

        def _num(tag: str, default: float = 0.0) -> float:
            v = by_tag.get(tag)
            return float(v.value) if v is not None else default

        net_liq = _num("NetLiquidation")
        cash = _num("TotalCashValue")
        realized = _num("RealizedPnL")
        unrealized = _num("UnrealizedPnL")
        currency = by_tag["NetLiquidation"].currency if "NetLiquidation" in by_tag else "EUR"

        return AccountSummary(
            net_liquidation=net_liq,
            cash_balance=cash,
            realized_pnl_today=realized,
            unrealized_pnl_today=unrealized,
            currency=currency,
        )

    def get_positions(self) -> list[Position]:
        ib = self._require_connection()
        positions = []
        for p in ib.positions(self.settings.account or ""):
            market_price = 0.0
            try:
                ticker = ib.reqMktData(p.contract, "", False, False)
                ib.sleep(0.5)
                market_price = ticker.marketPrice() or p.avgCost
            except Exception:  # pragma: no cover - best-effort live price lookup
                market_price = p.avgCost
            positions.append(
                Position(
                    symbol=p.contract.symbol,
                    quantity=int(p.position),
                    average_cost=float(p.avgCost),
                    market_price=float(market_price),
                )
            )
        return positions

    def get_last_price(self, symbol: str, exchange: str, currency: str) -> float:
        ib = self._require_connection()
        contract = self._make_contract(symbol, exchange, currency)
        ib.qualifyContracts(contract)
        ticker = ib.reqMktData(contract, "", False, False)
        ib.sleep(1.0)
        price = ticker.marketPrice()
        if price is None or price != price:  # NaN check
            price = ticker.close
        ib.cancelMktData(contract)
        if price is None or price <= 0:
            raise RuntimeError(f"Could not get a valid last price for {symbol}")
        return float(price)

    def place_order(self, order: Order) -> OrderResult:
        """Submit a real order to IBKR.

        Callers (the Kronos agent) are responsible for making sure this
        is only invoked after RiskManager AND a human approval gate have
        both signed off — this method does not re-check either.
        """
        from ib_insync import MarketOrder, LimitOrder

        ib = self._require_connection()
        contract = self._make_contract(order.symbol, order.exchange, order.currency)
        ib.qualifyContracts(contract)

        if order.order_type == "LMT":
            if order.limit_price is None:
                raise ValueError("limit_price is required for LMT orders")
            ib_order = LimitOrder(order.side.value, order.quantity, order.limit_price)
        else:
            ib_order = MarketOrder(order.side.value, order.quantity)

        logger.warning(
            "Submitting LIVE order to IBKR: %s %s %s @ %s",
            order.side.value,
            order.quantity,
            order.symbol,
            order.order_type,
        )
        trade = ib.placeOrder(contract, ib_order)
        ib.sleep(1.0)

        return OrderResult(
            order=order,
            status=trade.orderStatus.status or "SUBMITTED",
            broker_order_id=str(trade.order.orderId),
            fill_price=trade.orderStatus.avgFillPrice or None,
            message="Order submitted to IBKR",
        )
