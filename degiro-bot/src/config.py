import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Symbol:
    product_id: str
    name: str


@dataclass
class StrategyConfig:
    fast_ma_period: int
    slow_ma_period: int
    rsi_period: int
    rsi_buy_below: float
    rsi_sell_above: float


@dataclass
class RiskConfig:
    max_position_pct: float
    stop_loss_pct: float
    max_daily_loss_pct: float
    max_order_value: float


@dataclass
class Credentials:
    username: str
    password: str
    int_account: int | None
    totp_secret: str | None
    risk_confirmed: bool


@dataclass
class Config:
    symbols: list[Symbol]
    strategy: StrategyConfig
    risk: RiskConfig
    interval_minutes: int
    credentials: Credentials = field(repr=False)


def load_config(config_path: str | Path = BASE_DIR / "config.yaml",
                 env_path: str | Path = BASE_DIR / ".env") -> Config:
    load_dotenv(env_path)

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    symbols = [Symbol(**s) for s in raw["symbols"]]
    strategy = StrategyConfig(**raw["strategy"])
    risk = RiskConfig(**raw["risk"])

    int_account_raw = os.environ.get("DEGIRO_INT_ACCOUNT", "").strip()

    credentials = Credentials(
        username=os.environ.get("DEGIRO_USERNAME", ""),
        password=os.environ.get("DEGIRO_PASSWORD", ""),
        int_account=int(int_account_raw) if int_account_raw else None,
        totp_secret=os.environ.get("DEGIRO_TOTP_SECRET") or None,
        risk_confirmed=os.environ.get("I_UNDERSTAND_THE_RISK", "false").strip().lower() == "true",
    )

    if not credentials.username or not credentials.password:
        raise ValueError(
            "DEGIRO_USERNAME and DEGIRO_PASSWORD must be set in .env "
            "(copy .env.example to .env and fill in real values)."
        )

    return Config(
        symbols=symbols,
        strategy=strategy,
        risk=risk,
        interval_minutes=raw["schedule"]["interval_minutes"],
        credentials=credentials,
    )
