"""Central configuration for Kronos.

Every safety-relevant knob lives here and every one of them defaults to
the *safe* value:

- ``live_trading`` defaults to ``False`` (dry-run / paper only). It only
  becomes ``True`` if the ``KRONOS_LIVE_TRADING`` environment variable is
  set to ``true`` *explicitly*.
- Risk limits default to conservative, small amounts.
- Human approval before a live order is always ``True`` unless a config
  file explicitly disables it (not recommended, and still gated by
  ``live_trading``).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ImportError:  # pragma: no cover - optional dependency
    pass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class RiskLimits:
    """Hard caps enforced by the RiskManager before any order is placed."""

    max_order_value_eur: float = 500.0
    max_daily_loss_eur: float = 250.0
    max_position_value_eur: float = 2000.0
    max_orders_per_day: int = 10


@dataclass
class IBKRSettings:
    host: str = "127.0.0.1"
    port: int = 7497  # 7497 = TWS paper trading, 7496 = TWS live, 4002/4001 = Gateway
    client_id: int = 7
    account: str | None = None
    exchange: str = "AEB"  # Euronext Amsterdam, for Dutch equities
    currency: str = "EUR"


@dataclass
class KronosConfig:
    live_trading: bool = False
    require_human_approval: bool = True
    watchlist: list[str] = field(default_factory=lambda: ["ASML", "ADYEN", "INGA"])
    risk: RiskLimits = field(default_factory=RiskLimits)
    ibkr: IBKRSettings = field(default_factory=IBKRSettings)
    anthropic_api_key: str | None = None
    use_llm_vibe: bool = False

    @classmethod
    def from_env_and_file(cls, config_path: str | Path | None = None) -> "KronosConfig":
        data: dict[str, Any] = {}
        if config_path is not None:
            path = Path(config_path)
            if path.exists():
                if yaml is None:
                    raise RuntimeError(
                        "PyYAML is required to load a YAML config file. "
                        "Install it with `pip install pyyaml`."
                    )
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

        risk_data = data.get("risk", {})
        ibkr_data = data.get("ibkr", {})

        cfg = cls(
            live_trading=_env_bool("KRONOS_LIVE_TRADING", data.get("live_trading", False)),
            require_human_approval=_env_bool(
                "KRONOS_REQUIRE_APPROVAL", data.get("require_human_approval", True)
            ),
            watchlist=data.get("watchlist", ["ASML", "ADYEN", "INGA"]),
            risk=RiskLimits(
                max_order_value_eur=_env_float(
                    "KRONOS_MAX_ORDER_VALUE_EUR",
                    risk_data.get("max_order_value_eur", 500.0),
                ),
                max_daily_loss_eur=_env_float(
                    "KRONOS_MAX_DAILY_LOSS_EUR",
                    risk_data.get("max_daily_loss_eur", 250.0),
                ),
                max_position_value_eur=_env_float(
                    "KRONOS_MAX_POSITION_VALUE_EUR",
                    risk_data.get("max_position_value_eur", 2000.0),
                ),
                max_orders_per_day=int(
                    risk_data.get("max_orders_per_day", 10)
                ),
            ),
            ibkr=IBKRSettings(
                host=os.environ.get("KRONOS_IBKR_HOST", ibkr_data.get("host", "127.0.0.1")),
                port=int(os.environ.get("KRONOS_IBKR_PORT", ibkr_data.get("port", 7497))),
                client_id=int(
                    os.environ.get("KRONOS_IBKR_CLIENT_ID", ibkr_data.get("client_id", 7))
                ),
                account=os.environ.get("KRONOS_IBKR_ACCOUNT", ibkr_data.get("account")),
                exchange=ibkr_data.get("exchange", "AEB"),
                currency=ibkr_data.get("currency", "EUR"),
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            use_llm_vibe=_env_bool("KRONOS_USE_LLM_VIBE", data.get("use_llm_vibe", False)),
        )

        # Safety net: never allow live trading without human approval,
        # regardless of what a config file says.
        if cfg.live_trading and not cfg.require_human_approval:
            raise ValueError(
                "Refusing to start: live_trading=True requires "
                "require_human_approval=True. Real-money orders must "
                "always be confirmed by a human."
            )
        return cfg
