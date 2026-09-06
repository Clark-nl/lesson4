"""Human-in-the-loop confirmation before any live order is submitted.

Kronos never sends a real order without a human explicitly typing "yes"
at this gate. There is no config flag to bypass it while live_trading is
on (see kronos.config.KronosConfig.from_env_and_file, which refuses to
start otherwise).
"""
from __future__ import annotations

import abc
from datetime import datetime, timezone

from kronos.broker.base import AccountSummary, Order


class ApprovalGate(abc.ABC):
    @abc.abstractmethod
    def confirm(self, order: Order, estimated_value: float, account: AccountSummary) -> bool:
        """Return True if a human approved this exact order."""
        ...


class CLIApprovalGate(ApprovalGate):
    """Prompts on stdin/stdout. Used by the interactive CLI entrypoint."""

    def confirm(self, order: Order, estimated_value: float, account: AccountSummary) -> bool:
        print("\n" + "=" * 60)
        print(f"[Kronos] LIVE ORDER AWAITING YOUR APPROVAL "
              f"({datetime.now(timezone.utc).isoformat(timespec='seconds')})")
        print("=" * 60)
        print(f"  Symbol:          {order.symbol} ({order.exchange}/{order.currency})")
        print(f"  Side:            {order.side.value}")
        print(f"  Quantity:        {order.quantity}")
        print(f"  Order type:      {order.order_type}"
              + (f" @ {order.limit_price}" if order.limit_price else ""))
        print(f"  Estimated value: {estimated_value:.2f} {order.currency}")
        print(f"  Reason:          {order.reason or '(none given)'}")
        print(f"  Account cash:    {account.cash_balance:.2f} {account.currency}")
        print(f"  Today's P&L:     {account.total_pnl_today:+.2f} {account.currency}")
        print("-" * 60)
        answer = input("Type EXACTLY 'yes' to submit this order to the broker, "
                        "anything else to skip it: ").strip()
        approved = answer == "yes"
        print("[Kronos] Approved, submitting order." if approved
              else "[Kronos] Not approved, order skipped.")
        return approved


class AutoDenyApprovalGate(ApprovalGate):
    """Safe default for non-interactive contexts (e.g. cron jobs): always
    denies, so a live order is never silently sent without a human present."""

    def confirm(self, order: Order, estimated_value: float, account: AccountSummary) -> bool:
        return False


class CallbackApprovalGate(ApprovalGate):
    """Wraps an injectable callback, mainly for tests and non-CLI UIs
    (e.g. a Slack bot could implement its own callback that waits for a
    human's thumbs-up reaction)."""

    def __init__(self, callback) -> None:
        self._callback = callback

    def confirm(self, order: Order, estimated_value: float, account: AccountSummary) -> bool:
        return bool(self._callback(order, estimated_value, account))
