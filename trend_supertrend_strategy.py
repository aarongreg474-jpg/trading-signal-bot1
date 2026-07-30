"""
Third strategy: Moving Average(100) trend filter + ZigZag + SuperTrend(10,1)
+ RSI(10) confluence, on M1 candles, 3-minute expiry.

Rules (matching the described strategy):
1. MA(100) trend filter: price above MA -> look for bullish trades,
   price below MA -> look for bearish trades.
2. ZigZag: the current swing leg direction must match the trade direction.
3. SuperTrend: must currently be in that same direction, AND have flipped
   recently (a fresh flip, not one that happened many candles ago).
4. RSI(10): should be on the same side of 50 as the trade direction, and
   must NOT have been stuck in overbought/oversold for several bars in a
   row (that signals the move may already be exhausted).
5. Skip entirely if volatility (ATR) is unusually high right now.

Runs independently of the EMA/Vortex/MACD scalp strategy — either firing
sends its own separate Discord alert.
"""

import numpy as np
import pandas as pd

from indicators import calc_rsi, calc_atr
from config import (
    TREND_MA_PERIOD, ZIGZAG_WINDOW, ZIGZAG_LOOKBACK,
    SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER, TREND_RSI_PERIOD,
    SUPERTREND_FRESH_BARS, RSI_OVEREXTEND_BARS, TREND_ATR_VOLATILITY_MULT,
)


def calc_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def calc_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 1.0) -> pd.Series:
    atr = calc_atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    upperband = (hl2 + multiplier * atr).to_numpy().copy()
    lowerband = (hl2 - multiplier * atr).to_numpy().copy()
    close = df["close"].to_numpy()
    n = len(df)
    trend = np.ones(n, dtype=int)
    for i in range(1, n):
        if close[i] > upperband[i - 1]:
            trend[i] = 1
        elif close[i] < lowerband[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]
            if trend[i] == 1 and lowerband[i] < lowerband[i - 1]:
                lowerband[i] = lowerband[i - 1]
            if trend[i] == -1 and upperband[i] > upperband[i - 1]:
                upperband[i] = upperband[i - 1]
    return pd.Series(trend, index=df.index)


def find_swing_points(df: pd.DataFrame, window: int = 3, lookback: int = 60):
    recent = df.iloc[-lookback:]
    highs, lows = [], []
    for i in range(window, len(recent) - window):
        seg_h = recent["high"].iloc[i - window:i + window + 1]
        seg_l = recent["low"].iloc[i - window:i + window + 1]
        if recent["high"].iloc[i] == seg_h.max():
            highs.append((i, recent["high"].iloc[i]))
        if recent["low"].iloc[i] == seg_l.min():
            lows.append((i, recent["low"].iloc[i]))
    return highs, lows


def zigzag_direction(df: pd.DataFrame, window: int = 3, lookback: int = 60) -> int:
    """Current swing leg direction: 1 if the most recent pivot was a low
    (price now legging up from it), -1 if it was a high (legging down)."""
    highs, lows = find_swing_points(df, window, lookback)
    if not highs and not lows:
        return 0
    last_high_idx = highs[-1][0] if highs else -1
    last_low_idx = lows[-1][0] if lows else -1
    if last_low_idx > last_high_idx:
        return 1
    elif last_high_idx > last_low_idx:
        return -1
    return 0


def evaluate_trend_supertrend_signal(df: pd.DataFrame) -> dict:
    close = df["close"]

    ma = calc_sma(close, TREND_MA_PERIOD)
    if pd.isna(ma.iloc[-1]):
        ma_dir = 0
    else:
        ma_dir = 1 if close.iloc[-1] > ma.iloc[-1] else (-1 if close.iloc[-1] < ma.iloc[-1] else 0)

    zz_dir = zigzag_direction(df, ZIGZAG_WINDOW, ZIGZAG_LOOKBACK)

    st_trend = calc_supertrend(df, SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER)
    st_dir = int(st_trend.iloc[-1])
    recent_trend = st_trend.iloc[-(SUPERTREND_FRESH_BARS + 1):]
    st_fresh = recent_trend.nunique() > 1

    rsi = calc_rsi(close, TREND_RSI_PERIOD)
    rsi_val = rsi.iloc[-1]
    rsi_dir = 1 if rsi_val > 50 else (-1 if rsi_val < 50 else 0)
    recent_rsi = rsi.iloc[-RSI_OVEREXTEND_BARS:]
    rsi_overextended = (recent_rsi > 70).all() or (recent_rsi < 30).all()

    atr = calc_atr(df)
    atr_avg = atr.rolling(20).mean()
    high_volatility = (
        not pd.isna(atr.iloc[-1]) and not pd.isna(atr_avg.iloc[-1])
        and atr.iloc[-1] > TREND_ATR_VOLATILITY_MULT * atr_avg.iloc[-1]
    )

    final_signal = "NO SIGNAL"
    direction = 0

    all_agree = (ma_dir == zz_dir == st_dir) and ma_dir != 0
    rsi_ok = (rsi_dir == ma_dir or rsi_dir == 0) and not rsi_overextended

    if all_agree and st_fresh and rsi_ok and not high_volatility:
        direction = ma_dir
        final_signal = "CALL (BUY)" if direction == 1 else "PUT (SELL)"

    return {
        "final_signal": final_signal,
        "direction": direction,
        "ma_dir": ma_dir,
        "zigzag_dir": zz_dir,
        "supertrend_dir": st_dir,
        "supertrend_fresh": bool(st_fresh),
        "rsi_dir": rsi_dir,
        "rsi_overextended": bool(rsi_overextended),
        "high_volatility": bool(high_volatility),
  }
