"""Strategy interface: turns price history into a trading Signal."""
from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field

import pandas as pd


class Action(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    symbol: str
    action: Action
    confidence: float  # 0.0 - 1.0
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


class Strategy(abc.ABC):
    @abc.abstractmethod
    def generate_signal(self, symbol: str, price_history: pd.DataFrame) -> Signal:
        """price_history must be indexed by date with at least a 'close'
        column (and ideally 'volume')."""
        ...
