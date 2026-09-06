"""Configuration loading for the purchase-list pipeline.

Values come from a YAML file, with environment variables taking
precedence for anything secret (API keys/tokens). This keeps credentials
out of version control while letting non-secret tuning (thresholds, fee
tables) live in a committed config file.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ScoringConfig:
    min_margin_rate: float = 0.15
    min_stock_qty: int = 5
    top_n: int = 50
    demand_weight: float = 0.4
    margin_weight: float = 0.6


@dataclass
class PipelineConfig:
    platform: str
    channels: list[str]
    scoring: ScoringConfig
    channel_fees: dict[str, dict[str, float]]
    output_dir: str = "output"
    raw: dict[str, Any] = field(default_factory=dict)


def load_config(path: str) -> PipelineConfig:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    scoring_raw = raw.get("scoring", {})
    scoring = ScoringConfig(
        min_margin_rate=scoring_raw.get("min_margin_rate", 0.15),
        min_stock_qty=scoring_raw.get("min_stock_qty", 5),
        top_n=scoring_raw.get("top_n", 50),
        demand_weight=scoring_raw.get("demand_weight", 0.4),
        margin_weight=scoring_raw.get("margin_weight", 0.6),
    )

    config = PipelineConfig(
        platform=raw.get("platform", "ownerclan"),
        channels=raw.get("channels", ["shopify"]),
        scoring=scoring,
        channel_fees=raw.get("channel_fees", {}),
        output_dir=raw.get("output_dir", "output"),
        raw=raw,
    )
    _validate(config, path)
    return config


def _validate(config: PipelineConfig, path: str) -> None:
    errors = []

    if not config.platform or not isinstance(config.platform, str):
        errors.append("'platform' must be a non-empty string.")

    if not config.channels or not isinstance(config.channels, list):
        errors.append("'channels' must be a non-empty list, e.g. channels: [shopify].")

    scoring = config.scoring
    if not (0 <= scoring.min_margin_rate < 1):
        errors.append(
            f"scoring.min_margin_rate must be in [0, 1) - got {scoring.min_margin_rate}."
        )
    if scoring.min_stock_qty < 0:
        errors.append(f"scoring.min_stock_qty must be >= 0 - got {scoring.min_stock_qty}.")
    if scoring.top_n < 1:
        errors.append(f"scoring.top_n must be >= 1 - got {scoring.top_n}.")
    if scoring.margin_weight < 0 or scoring.demand_weight < 0:
        errors.append("scoring.margin_weight and demand_weight must both be >= 0.")

    for channel, fees in config.channel_fees.items():
        commission = fees.get("commission_rate", 0.0)
        payment_fee = fees.get("payment_fee_rate", 0.0)
        fixed_fee = fees.get("fixed_fee", 0.0)
        if commission < 0 or payment_fee < 0 or fixed_fee < 0:
            errors.append(f"channel_fees.{channel}: rates/fees must be >= 0.")
        elif commission + payment_fee >= 1:
            errors.append(
                f"channel_fees.{channel}: commission_rate + payment_fee_rate must be < 1 "
                f"(got {commission + payment_fee}) - a channel can't take >= 100% of the sale price."
            )

    if errors:
        raise ValueError(
            f"Invalid config at {path}:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    for channel in config.channels:
        if channel != "shopify" and channel not in config.channel_fees:
            logger.warning(
                "Channel '%s' has no entry under channel_fees in %s - it will be scored "
                "with 0%% fees, which likely overstates its margin.",
                channel,
                path,
            )


def env_or(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
