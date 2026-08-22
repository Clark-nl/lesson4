import numpy as np
import pandas as pd


def simple_moving_average(prices: pd.Series, period: int) -> pd.Series:
    return prices.rolling(window=period, min_periods=period).mean()


def relative_strength_index(prices: pd.Series, period: int) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # avg_loss == 0 makes the division above NaN; resolve those edge cases
    # explicitly: no losses at all -> RSI 100, unless there were no gains
    # either (flat price) -> RSI 50 (neutral).
    rsi = rsi.mask(avg_loss == 0, 100.0)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    return rsi.fillna(50)
