"""Read-only connectivity check. Places NO orders.

Run this once against your real account after filling in .env / config.yaml,
before ever setting I_UNDERSTAND_THE_RISK=true. It logs in, prints your
account totals, and fetches price history for each configured symbol so you
can confirm the DeGiro connection and parsing actually work for your account.

Usage (from the degiro-bot/ directory):
    python -m scripts.inspect_account
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.degiro_client import DegiroClient


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = load_config()
    client = DegiroClient(config.credentials)

    print("Connecting to DeGiro...")
    client.connect()
    print(f"Connected. int_account={client.int_account}")

    portfolio_value = client.get_portfolio_value()
    cash_available = client.get_cash_available()
    print(f"Portfolio value: {portfolio_value}")
    print(f"Cash available (EUR): {cash_available}")

    if portfolio_value == 0.0:
        print("WARNING: portfolio value came back as 0. This may be correct, or it may mean "
              "_flatten_value_list()/the 'totalPortfolio' key assumption in degiro_client.py "
              "doesn't match your account's response shape. Inspect manually if unexpected.")

    for symbol in config.symbols:
        print(f"\n--- {symbol.name} (product_id={symbol.product_id}) ---")
        position_value = client.get_position_value(symbol.product_id)
        print(f"Position value: {position_value}")

        prices = client.get_price_history(symbol.product_id, days=60)
        if prices.empty:
            print("WARNING: no price history returned. Check the product_id and that "
                  "the 'ohlc:issueid:<product_id>' series format is correct for this product.")
        else:
            print(f"Price history: {len(prices)} points, last close={prices.iloc[-1]} "
                  f"at {prices.index[-1]}")

    print("\nDone. No orders were placed.")


if __name__ == "__main__":
    main()
