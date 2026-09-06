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

### Opening and configuring your IBKR account (do this once)

This is the part most people get stuck on, since it happens entirely on
IBKR's website/app and has nothing to do with the code in this repo.

1. **Account type.** Choose **Cash Account**, not Margin. Kronos never
   borrows or shorts, and all of its risk limits assume positions are
   paid for in full with cash. A margin account lets you (or a bug)
   lose more than the account is worth, which defeats the point of the
   caps in `config/kronos.yaml`.
2. **Base currency.** Set it to **EUR** if most of your trading will be
   on Euronext Amsterdam (AEB). If your account's base currency is
   something else (e.g. USD), buying EUR-denominated stocks will
   trigger automatic FX conversion (and FX fees) on every trade unless
   you hold EUR cash yourself — see "Funding & currency" below.
3. **Trading permissions / products.** During account opening (or later
   under `Settings → Account Settings → Trading Experience & Permissions`),
   make sure **Stocks** is enabled for the **Netherlands (Euronext
   Amsterdam)** exchange specifically — IBKR asks about trading
   experience per exchange/product and won't let you place AEB orders
   until that's approved. Add other Euronext markets (Brussels, Paris)
   too if your watchlist ever includes them.
4. **Stock Yield Enhancement Program.** This is IBKR lending out shares
   you hold to other traders (e.g. short sellers) for a fee. It's
   unrelated to trading itself. Recommendation for use with Kronos:
   **leave it unchecked / not enrolled** — Kronos doesn't account for
   shares being on loan, and it adds tax/settlement complexity for no
   benefit to what the bot does. You can always enable it later by
   itself, separately from the bot.
5. **Market data subscriptions.** This is the step most likely to break
   `IBKRBroker.get_last_price()` silently: by default a new account has
   **no live European market data**, only delayed (15-minute) quotes.
   Go to `Settings → User Settings → Market Data Subscriptions` and
   subscribe to at least **"Euronext Amsterdam, Brussels, Lisbon, Paris"**
   (a small monthly fee, often waived if your commissions exceed it).
   Without this, `reqMktData` can return `NaN`/stale prices and Kronos
   will raise `RuntimeError("Could not get a valid last price ...")`.
6. **KYC / financial questionnaire** (annual net income, net worth,
   trading experience, etc.) — this is a regulatory requirement IBKR
   needs directly from you; answer accurately, Kronos has no part in it.
7. **Funding & currency.** Wire or transfer EUR into the account. If you
   fund in another currency, either convert to EUR yourself in
   `Client Portal → Transfer & Pay → Currency Conversion` before trading,
   or accept that IBKR will do it automatically at trade time (worse
   FX rate, extra step to review in your account activity).
8. **Paper trading account.** Once your live application is submitted
   (it doesn't have to be fully approved yet), IBKR automatically
   provisions a linked **paper trading account** with simulated money —
   this is what step "Running against IBKR paper trading" below uses,
   and there's no reason to skip straight to real money.

### Installing TWS / IB Gateway and enabling the API (detailed walkthrough)

`ib_insync` (what `kronos/broker/ibkr.py` uses) does not talk to IBKR's
cloud directly — it talks over a local socket to a copy of **Trader
Workstation (TWS)** or **IB Gateway** running somewhere reachable from
Kronos. That local program is the only thing actually authenticated to
IBKR; Kronos just connects to it. So this step has to work before
anything in `kronos/` can reach a real (or paper) account.

**1. Choose TWS or IB Gateway.**
- **TWS** is the full desktop trading platform (charts, order book,
  scanners, ...). Heavier, but useful while you're still watching what
  the bot does by hand.
- **IB Gateway** is the same API/connection engine with no trading UI —
  smaller, uses less memory, and is what IBKR recommends for running an
  automated client like Kronos unattended on a server. The API setup
  below is identical for both; only the menu layout differs slightly.

Download from the [IBKR software page](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
(pick "Stable" unless you specifically need the "Latest" beta channel —
stable is what you want for something that trades real money) and
install for your OS (Windows/macOS/Linux all supported; on Linux it's a
`.sh` installer you run with `bash`).

**2. Log in.**
Launch TWS or IB Gateway. On the login screen:
- Pick **"IB API"** (not "FIX API") if IB Gateway asks which mode.
- Use the **Paper Trading** radio button/toggle and your paper
  username the first few times (see "Opening and configuring your IBKR
  account" above — the paper login is a separate username IBKR
  auto-generates, not your live one with a flag). Switch to your live
  username only once you're actually going live.
- There's a small gear/settings icon on the login screen itself
  ("Configure API settings before login") — you can preconfigure the
  API port and Trusted IPs there without fully logging in first, which
  is convenient on a fresh install.

**3. Enable the API.**
Once logged in: `File → Global Configuration` (macOS: the app menu
instead of `File`) → left sidebar `API → Settings`. Set:
- ☑ **Enable ActiveX and Socket Clients** — the master switch; without
  this, `connect()` will simply time out.
- ☐ **Read-Only API** — **uncheck** this. It's checked by default on
  fresh installs and silently blocks every order Kronos tries to place
  (reads like account/positions still work, which makes this a
  confusing failure to debug — the order just never appears at IBKR
  with no error on the TWS side).
- **Socket port** — note the value, default `7497` for TWS paper,
  `7496` for TWS live, `4002` for Gateway paper, `4001` for Gateway
  live. This must match `ibkr.port` / `KRONOS_IBKR_PORT` exactly.
- **Trusted IP Addresses** → add `127.0.0.1` if Kronos runs on the same
  machine (the default, recommended setup). If Kronos runs elsewhere,
  add its IP here instead of opening the port to everyone — see the
  security note further down.
- ☑ **Create API message log file** is worth turning on the first time;
  it gives you a real transcript to read when a connection or order
  silently fails.
- Leave **Master API client ID** blank unless you specifically want to
  restrict which `client_id` values may connect.
- Click **Apply**, then **OK**.

**4. Point Kronos at it.**
In `config/kronos.yaml` (or via `KRONOS_IBKR_*` env vars):
```yaml
ibkr:
  host: 127.0.0.1
  port: 7497        # must match the socket port from step 3
  client_id: 7       # any integer not already used by another API client on this TWS/Gateway
  account: null      # your account id, or leave null for the default
```
Each simultaneous connection (Kronos, plus e.g. an `ib_insync` Jupyter
notebook you might also have open) needs its own unique `client_id` —
reusing one that's already connected causes IBKR to silently disconnect
the older session.

**5. Verify the connection** before trusting Kronos with it:
```bash
python -c "
from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=7)
print('Connected:', ib.isConnected())
print(ib.accountSummary())
ib.disconnect()
"
```
If this hangs or raises `TimeoutError`, the API isn't enabled or the
port doesn't match (step 3). If it connects but `accountSummary()` is
empty, you're likely not logged into the account you expect, or the
paper/live account pairing is off.

**6. Keep it running.** TWS/Gateway must be **open and logged in**
whenever Kronos runs — there's no headless "just an API key" mode, this
local program is the whole authenticated bridge to IBKR. Two things to
configure for anything longer than a manual test session:
- IBKR force-logs-out TWS/Gateway roughly once every 24 hours for
  maintenance. Under `Configuration → Lock and Exit`, enable
  **Auto restart** (TWS) so it restarts itself and reconnects instead
  of just sitting disconnected until you notice.
- Consider running IB Gateway under a process supervisor (systemd,
  `supervisord`, a `screen`/`tmux` session at minimum) so it comes back
  after a machine reboot or crash.

**7. Common connection errors:**
| Symptom | Likely cause |
|---|---|
| `TimeoutError` / connection refused | API not enabled, or wrong port |
| Connects, then immediately disconnects | `client_id` already in use by another session |
| Orders never show up in TWS, no error | "Read-Only API" still checked |
| `reqMktData` returns `NaN`/stale price | missing market data subscription (see account setup above), or market is closed |
| Works, then silently stops after ~24h | daily forced logout — enable auto-restart |

Once connected, all the same risk limits and the approval prompt in
Kronos still apply against a paper account — this is the right place to
rehearse the full flow (including a few real BUY/SELL round trips)
before ever touching a live account.

### Going live (real money)

```bash
KRONOS_LIVE_TRADING=true python scripts/run_kronos.py --config config/kronos.yaml
```

- Make sure `ibkr.port` points at your **live** TWS/Gateway port
  (`7496` for TWS, `4001` for Gateway), and that you understand the
  risk limits in your config — they are real caps on real money.
- You will be prompted to type `yes` for every single order before it
  is sent to IBKR.
- **Security note:** the TWS/IB Gateway API port has no authentication
  of its own beyond "Trusted IPs" — anyone who can reach that port on
  your machine can trade on your account. Never expose it to the
  internet directly; if Kronos runs on a different machine than
  TWS/Gateway, put it behind a VPN or SSH tunnel rather than opening
  the port publicly.

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
