"""Thin wrapper around degiro-connector (tested against v3.0.36).

DeGiro has no official public API. This wraps the reverse-engineered,
community-maintained `degiro-connector` library. Its behavior can change
without notice, and heavy automated use may violate DeGiro's terms of
service. Use at your own risk and review DeGiro's terms before running
this against a real account.

The shapes of `get_update`'s portfolio/cash_funds/total_portfolio payloads
are NOT pydantic-typed by the library (they come back as raw dicts) — the
parsing here follows DeGiro's long-standing "list of {name, value} pairs"
format, verified against the library's source but not against a live
account (no test credentials were available while writing this). Run
`scripts/inspect_account.py` once against your real account before relying
on the parsed numbers, and adjust `_flatten_value_list` / `_find_position`
below if DeGiro's response shape has changed.
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
from degiro_connector.quotecast.models.chart import ChartRequest, Interval
from degiro_connector.quotecast.tools.chart_fetcher import ChartFetcher, SeriesFormatter
from degiro_connector.trading.api import API as TradingAPI
from degiro_connector.trading.models.account import UpdateOption, UpdateRequest
from degiro_connector.trading.models.credentials import Credentials as DegiroCredentials
from degiro_connector.trading.models.order import Action, Order, OrderType, TimeType

from .config import Credentials as AppCredentials

logger = logging.getLogger(__name__)


def _flatten_value_list(raw: dict | None) -> dict:
    """DeGiro's update endpoint returns {"value": [{"name": x, "value": y}, ...]}
    for scalar sections (cashFunds/totalPortfolio entries). Flatten to {x: y}."""
    if not raw:
        return {}
    return {item["name"]: item.get("value") for item in raw.get("value", []) if "name" in item}


def _iter_positions(raw: dict | None):
    """Portfolio entries are {"value": [{"id": ..., "value": [{"name","value"}, ...]}, ...]}."""
    if not raw:
        return
    for entry in raw.get("value", []):
        yield _flatten_value_list(entry)


class DegiroClient:
    def __init__(self, credentials: AppCredentials):
        self._creds = DegiroCredentials(
            username=credentials.username,
            password=credentials.password,
            int_account=credentials.int_account,
            totp_secret_key=credentials.totp_secret,
        )
        self._api = TradingAPI(credentials=self._creds)
        self._chart_fetcher: ChartFetcher | None = None

    @property
    def int_account(self) -> int | None:
        return self._creds.int_account

    def connect(self) -> None:
        self._api.connect.call()

        client_details = self._api.get_client_details.call()
        data = (client_details or {}).get("data", {})

        if self._creds.int_account is None:
            int_account = data.get("intAccount")
            if int_account is None:
                raise RuntimeError(
                    "Could not determine intAccount; set DEGIRO_INT_ACCOUNT explicitly in .env."
                )
            self._creds.int_account = int_account

        user_token = data.get("id")
        if user_token is None:
            raise RuntimeError("Could not determine user_token (client id) for price history.")
        self._chart_fetcher = ChartFetcher(user_token=user_token)

        logger.info("Connected to DeGiro (int_account=%s)", self._creds.int_account)

    def _get_update(self, *options: UpdateOption):
        request_list = [UpdateRequest(option=opt, last_updated=0) for opt in options]
        return self._api.get_update.call(request_list=request_list)

    def get_portfolio_value(self) -> float:
        update = self._get_update(UpdateOption.TOTAL_PORTFOLIO)
        totals = _flatten_value_list(update.total_portfolio)
        return float(totals.get("totalPortfolio", 0.0))

    def get_cash_available(self) -> float:
        update = self._get_update(UpdateOption.CASH_FUNDS)
        for entry in _iter_positions(update.cash_funds):
            if entry.get("currencyCode") == "EUR" or entry.get("currency") == "EUR":
                return float(entry.get("value", 0.0))
        return 0.0

    def get_position_value(self, product_id: str) -> float:
        update = self._get_update(UpdateOption.PORTFOLIO)
        for entry in _iter_positions(update.portfolio):
            if str(entry.get("id") or entry.get("productId")) == str(product_id):
                return float(entry.get("value", 0.0))
        return 0.0

    def get_price_history(self, product_id: str, days: int = 120) -> pd.Series:
        assert self._chart_fetcher is not None, "call connect() first"

        period = Interval.P1Y if days > 180 else Interval.P6M
        chart_request = ChartRequest(
            culture="en-US",
            period=period,
            requestid="1",
            resolution=Interval.P1D,
            series=[f"ohlc:issueid:{product_id}"],
            tz="Europe/Amsterdam",
        )
        chart = self._chart_fetcher.get_chart(chart_request=chart_request)
        if chart is None or not chart.series:
            return pd.Series(dtype=float)

        df = SeriesFormatter.format_series(series=chart.series[0])
        if "close" not in df.columns:
            return pd.Series(dtype=float)

        series = pd.Series(data=df["close"].to_list(), index=df["timestamp"].to_list())
        return series.sort_index()

    def place_order(self, *, product_id: str, side: str, quantity: int) -> str:
        order = Order(
            product_id=int(product_id),
            buy_sell=Action.BUY if side == "BUY" else Action.SELL,
            order_type=OrderType.MARKET,
            time_type=TimeType.GOOD_TILL_DAY,
            size=quantity,
        )
        checked = self._api.check_order.call(order=order)
        confirmed = self._api.confirm_order.call(confirmation_id=checked.confirmation_id, order=order)
        logger.info("Placed %s order for product %s: qty=%s -> order_id=%s",
                    side, product_id, quantity, confirmed.order_id)
        return confirmed.order_id
