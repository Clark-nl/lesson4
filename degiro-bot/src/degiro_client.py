"""Thin wrapper around degiro-connector.

degiro-connector talks to an unofficial, reverse-engineered DeGiro API.
It is not sanctioned by DeGiro; behavior can change or break without notice,
and heavy automated use may violate DeGiro's terms of service. Use at your
own risk and review DeGiro's terms before running this against a real account.
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
from degiro_connector.trading.api import API as TradingAPI
from degiro_connector.trading.models.credentials import Credentials as DegiroCredentials
from degiro_connector.trading.models.order import Order

from .config import Credentials as AppCredentials

logger = logging.getLogger(__name__)


class DegiroClient:
    def __init__(self, credentials: AppCredentials):
        self._creds = DegiroCredentials(
            username=credentials.username,
            password=credentials.password,
            int_account=credentials.int_account,
            totp_secret_key=credentials.totp_secret,
        )
        self._api = TradingAPI(credentials=self._creds)
        self._connected = False

    def connect(self) -> None:
        self._api.connect()
        self._connected = True
        logger.info("Connected to DeGiro")

    def get_portfolio_value(self) -> float:
        account_info = self._api.get_account_info()
        return float(account_info.total_portfolio_value)

    def get_cash_available(self) -> float:
        account_info = self._api.get_account_info()
        return float(account_info.total_cash_fund_value)

    def get_position_value(self, product_id: str) -> float:
        positions = self._api.get_positions()
        for p in positions:
            if str(p.product_id) == str(product_id):
                return float(p.value)
        return 0.0

    def get_price_history(self, product_id: str, days: int = 120) -> pd.Series:
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        candles = self._api.get_price_series(
            product_id=product_id,
            start=start,
            end=end,
        )
        series = pd.Series(
            data=[c.close for c in candles],
            index=[c.timestamp for c in candles],
        )
        return series.sort_index()

    def place_order(self, *, product_id: str, side: str, quantity: int) -> str:
        order = Order(
            product_id=product_id,
            action=Order.Action.BUY if side == "BUY" else Order.Action.SELL,
            order_type=Order.OrderType.MARKET,
            time_type=Order.TimeType.DAY,
            size=quantity,
        )
        checked = self._api.check_order(order=order)
        confirmed = self._api.confirm_order(confirmation_id=checked.confirmation_id, order=order)
        logger.info("Placed %s order for product %s: qty=%s -> %s", side, product_id, quantity, confirmed)
        return confirmed.order_id
