"""Configuration loading for the purchase-list pipeline.

Values come from a YAML file, with environment variables taking
precedence for anything secret (API keys/tokens). This keeps credentials
out of version control while letting non-secret tuning (thresholds, fee
tables) live in a committed config file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml


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

    return PipelineConfig(
        platform=raw.get("platform", "ownerclan"),
        channels=raw.get("channels", ["shopify"]),
        scoring=scoring,
        channel_fees=raw.get("channel_fees", {}),
        output_dir=raw.get("output_dir", "output"),
        raw=raw,
    )


def env_or(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
