# lesson4
# Sample-repository
This is a sample repository.
We have edited the README file.
##

## Kronos — a fund manager agent (vibe trading edition)

Kronos is a "vibe coded" fund manager agent for Dutch/European equities.
It reads price momentum (and, optionally, an AI-generated "news vibe"),
turns that into BUY/SELL/HOLD signals, and can execute real trades
through Interactive Brokers (IBKR) — but only with hard risk limits and
a human confirming every single live order.

> **This is not investment advice, and trading involves real risk of
> loss.** Kronos is provided as-is for personal/educational use. Test
> extensively in dry-run and IBKR paper trading before ever enabling
> `live_trading`.

### How it works

```
price history (Yahoo Finance) ──▶ VibeStrategy ──▶ Signal (BUY/SELL/HOLD)
                                                          │
                                                          ▼
                                          RiskManager.validate_order
                                     (per-order cap, daily loss cap,
                                      position cap, daily order cap)
                                                          │
                                        only when live_trading=true
                                                          ▼
                                        ApprovalGate.confirm (human)
                                                          │
                                                          ▼
                                          Broker.place_order (IBKR)
```

When `live_trading` is `false` (the **default**), Kronos runs this
entire pipeline against an in-memory `FakeBroker` instead — so you can
see exactly what it would have done, with a simulated cash balance and
positions, without connecting to IBKR or risking anything.

### Safety by default

- **Dry-run by default.** Real orders require `KRONOS_LIVE_TRADING=true`
  (or `live_trading: true` in the config file) set *explicitly*.
- **Hard risk limits**, enforced in code before any order is built:
  - `max_order_value_eur` — cap on any single order
  - `max_daily_loss_eur` — trading halts for the day once breached
  - `max_position_value_eur` — cap on total exposure per symbol
  - `max_orders_per_day` — cap on order count
- **Human approval is mandatory for live orders.** Kronos refuses to
  even start if `live_trading=true` and `require_human_approval=false`
  are combined. In the CLI, every live order is printed in full and you
  must type `yes` to submit it.
- No shorting: SELL signals only ever close an existing long position.

### Project layout

```
kronos/
  config.py            # env + YAML config, all safety knobs default safe
  broker/
    base.py            # Broker interface + Order/Position/AccountSummary
    fake.py            # in-memory broker used for dry-run + tests
    ibkr.py            # Interactive Brokers implementation (ib_insync)
  data/
    market_data.py     # OHLCV history via Yahoo Finance (yfinance)
  strategy/
    base.py            # Strategy interface + Signal/Action
    vibe.py            # VibeStrategy: momentum + RSI + volume (+ optional AI news vibe)
  risk/
    guardrails.py       # RiskManager: hard caps, fails closed
  approval/
    human_approval.py  # CLIApprovalGate and friends
  agent/
    fund_manager.py     # Kronos: wires everything together
scripts/
  run_kronos.py         # CLI entrypoint
config/
  kronos.example.yaml   # copy to kronos.yaml and edit
tests/                  # unit tests, all run against FakeBroker + synthetic data
```

### Setup

```bash
pip install -r requirements.txt
cp .env.example .env            # fill in as needed
cp config/kronos.example.yaml config/kronos.yaml
```

### Running in dry-run (recommended first)

```bash
python scripts/run_kronos.py --config config/kronos.yaml
```

This fetches recent price history for your watchlist, generates
signals, and "executes" any BUY/SELL against a simulated `FakeBroker`
account. Nothing leaves your machine.

### Running against IBKR paper trading

1. Install [Trader Workstation (TWS)](https://www.interactivebrokers.com/en/trading/tws.php)
   or IB Gateway, and log in to a **paper trading** account.
2. In TWS/Gateway: `Configuration → API → Settings` → enable
   "Enable ActiveX and Socket Clients", and note the socket port
   (default `7497` for TWS paper).
3. Set `ibkr.port` in your config (or `KRONOS_IBKR_PORT`) to match.
4. Even with `live_trading=true` against a paper account, all the same
   risk limits and the approval prompt still apply — this is the right
   place to rehearse the full flow before ever touching a live account.

### Going live (real money)

```bash
KRONOS_LIVE_TRADING=true python scripts/run_kronos.py --config config/kronos.yaml
```

- Make sure `ibkr.port` points at your **live** TWS/Gateway port
  (`7496` for TWS, `4001` for Gateway), and that you understand the
  risk limits in your config — they are real caps on real money.
- You will be prompted to type `yes` for every single order before it
  is sent to IBKR.

### Tests

```bash
pytest
```

All tests run against `FakeBroker` and synthetic price data — no
network access or IBKR connection required.

### Customizing the strategy

`VibeStrategy` (in `kronos/strategy/vibe.py`) is intentionally simple
and fully inspectable: momentum (short vs. long moving average), RSI,
and a volume-surge multiplier combine into a single "vibe score" that
becomes a BUY/SELL/HOLD signal with a confidence and human-readable
reasons. It also has an optional hook (`LLMVibeAnalyzer`, disabled by
default) to blend in an AI-generated sentiment read of recent
headlines. Swap in your own strategy by implementing the `Strategy`
interface in `kronos/strategy/base.py`.
