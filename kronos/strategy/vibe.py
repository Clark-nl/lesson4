"""VibeStrategy: a small, transparent "market vibe" signal.

"Vibe trading" here means: read the recent price action's *vibe* --
momentum, relative strength and volume interest -- and, optionally,
blend in an AI-generated read of the news "vibe" (headline sentiment)
for the same symbol. Every component is a plain, inspectable number so
a human can see exactly why Kronos wants to buy, sell, or do nothing.

This is intentionally simple. It is not investment advice, and it is
not meant to be a sophisticated alpha model -- it is a clear, testable
default strategy that plugs into the Strategy interface, which anyone
can swap out for something more serious.
"""
from __future__ import annotations

import logging

import pandas as pd

from kronos.strategy.base import Action, Signal, Strategy

logger = logging.getLogger("kronos.strategy.vibe")


def _sma(series: pd.Series, window: int) -> float:
    if len(series) < window:
        window = len(series)
    return float(series.tail(window).mean())


def _rsi(close: pd.Series, window: int = 14) -> float:
    if len(close) < 2:
        return 50.0
    window = min(window, len(close) - 1)
    delta = close.diff().dropna()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.tail(window).mean()
    avg_loss = losses.tail(window).mean()
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def _volume_surge(volume: pd.Series, window: int = 20) -> float:
    """Ratio of the most recent volume to its recent average (1.0 = normal)."""
    if volume is None or len(volume) < 2:
        return 1.0
    window = min(window, len(volume) - 1)
    baseline = volume.iloc[-(window + 1):-1].mean()
    if not baseline or baseline != baseline:  # NaN or zero
        return 1.0
    return float(volume.iloc[-1] / baseline)


class LLMVibeAnalyzer:
    """Optional AI read of news-headline sentiment for a symbol.

    Disabled unless explicitly enabled with an ANTHROPIC_API_KEY, so the
    default strategy never depends on a network call or API key.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-5") -> None:
        self.api_key = api_key
        self.model = model

    def score_headlines(self, symbol: str, headlines: list[str]) -> tuple[float, str]:
        """Returns (score in [-1, 1], one-line explanation)."""
        if not headlines:
            return 0.0, "no headlines supplied"

        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "The anthropic package is required for LLM vibe analysis. "
                "Install it with `pip install anthropic`."
            ) from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        prompt = (
            f"You are a neutral financial news sentiment scorer for {symbol}. "
            "Given these recent headlines, respond with a single line in the "
            "exact format `SCORE: <number> REASON: <short reason>`, where "
            "<number> is between -1.0 (very negative) and 1.0 (very positive).\n\n"
            + "\n".join(f"- {h}" for h in headlines)
        )
        response = client.messages.create(
            model=self.model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        score = 0.0
        reason = text.strip()
        try:
            score_part = text.split("SCORE:")[1].split("REASON:")[0].strip()
            score = max(-1.0, min(1.0, float(score_part)))
            reason = text.split("REASON:")[1].strip()
        except (IndexError, ValueError):
            logger.warning("Could not parse LLM vibe response: %r", text)
        return score, reason


class VibeStrategy(Strategy):
    def __init__(
        self,
        short_window: int = 10,
        long_window: int = 50,
        buy_threshold: float = 0.3,
        sell_threshold: float = -0.3,
        llm_analyzer: LLMVibeAnalyzer | None = None,
        news_provider: "callable | None" = None,
    ) -> None:
        self.short_window = short_window
        self.long_window = long_window
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.llm_analyzer = llm_analyzer
        # news_provider(symbol) -> list[str] of recent headlines; only used
        # when an llm_analyzer is configured.
        self.news_provider = news_provider

    def generate_signal(self, symbol: str, price_history: pd.DataFrame) -> Signal:
        if price_history is None or price_history.empty:
            return Signal(symbol, Action.HOLD, 0.0, ["no price data available"])

        close = price_history["close"]
        volume = price_history["volume"] if "volume" in price_history else None

        short_ma = _sma(close, self.short_window)
        long_ma = _sma(close, self.long_window)
        momentum = 0.0 if long_ma == 0 else (short_ma - long_ma) / long_ma
        momentum_score = max(-1.0, min(1.0, momentum * 10))  # scale to [-1, 1]-ish

        rsi = _rsi(close)
        # RSI 50 is neutral; >70 overbought (bearish tilt), <30 oversold (bullish tilt)
        rsi_score = max(-1.0, min(1.0, (50 - rsi) / 50))

        vol_surge = _volume_surge(volume) if volume is not None else 1.0
        # More-than-normal volume amplifies whatever direction momentum says;
        # capped so a quiet, illiquid spike can't dominate the score.
        volume_weight = max(0.5, min(1.5, vol_surge))

        price_vibe = ((momentum_score * 0.7) + (rsi_score * 0.3)) * volume_weight
        price_vibe = max(-1.0, min(1.0, price_vibe))

        reasons = [
            f"momentum(sma{self.short_window}={short_ma:.2f} vs "
            f"sma{self.long_window}={long_ma:.2f}) -> {momentum_score:+.2f}",
            f"RSI={rsi:.1f} -> {rsi_score:+.2f}",
            f"volume_surge={vol_surge:.2f}x",
        ]

        news_score = 0.0
        news_weight = 0.0
        if self.llm_analyzer is not None and self.news_provider is not None:
            headlines = self.news_provider(symbol) or []
            if headlines:
                news_score, news_reason = self.llm_analyzer.score_headlines(symbol, headlines)
                news_weight = 0.4
                reasons.append(f"AI news vibe={news_score:+.2f} ({news_reason})")

        combined = price_vibe * (1 - news_weight) + news_score * news_weight
        combined = max(-1.0, min(1.0, combined))

        if combined >= self.buy_threshold:
            action = Action.BUY
        elif combined <= self.sell_threshold:
            action = Action.SELL
        else:
            action = Action.HOLD

        confidence = min(1.0, abs(combined))
        return Signal(symbol=symbol, action=action, confidence=confidence, reasons=reasons)
