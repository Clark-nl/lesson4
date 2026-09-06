#!/usr/bin/env python3
"""CLI entrypoint for Kronos.

Examples
--------
Dry-run (default, no real orders, no IBKR connection needed):

    python scripts/run_kronos.py --config config/kronos.example.yaml

Live trading against Interactive Brokers (TWS/Gateway must already be
running locally with the API enabled). Every order still requires you
to type "yes" at the prompt:

    KRONOS_LIVE_TRADING=true python scripts/run_kronos.py \\
        --config config/kronos.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kronos.agent.fund_manager import Kronos  # noqa: E402
from kronos.config import KronosConfig  # noqa: E402
from kronos.logging_utils import configure_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Kronos fund manager agent.")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a YAML config file (see config/kronos.example.yaml).",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Run a single cycle for this symbol instead of the full watchlist "
             "(can be repeated).",
    )
    args = parser.parse_args()

    configure_logging()
    config = KronosConfig.from_env_and_file(args.config)

    mode = "LIVE TRADING" if config.live_trading else "DRY RUN (paper/simulation)"
    print(f"[Kronos] Starting in {mode} mode.")
    if config.live_trading:
        print(
            "[Kronos] Real orders may be submitted to Interactive Brokers. "
            "Every order still requires your explicit 'yes'."
        )

    kronos = Kronos(config)

    if args.symbols:
        for symbol in args.symbols:
            kronos.run_cycle(symbol)
        report_positions = kronos.broker.get_positions()
        account = kronos.broker.get_account_summary()
        print(f"\nAccount: net_liq={account.net_liquidation:.2f} "
              f"cash={account.cash_balance:.2f} pnl_today={account.total_pnl_today:+.2f}")
        for p in report_positions:
            print(f"  {p.symbol}: {p.quantity} @ {p.average_cost:.2f}")
    else:
        report = kronos.run_watchlist_cycle()
        print()
        print(report.as_text())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
