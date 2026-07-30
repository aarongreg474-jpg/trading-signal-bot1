"""
Second, independent strategy: EMA(3/10) + Vortex(10) + MACD(15,27,9) scalp
confluence, on M1 candles only, 1-minute expiry.

Rules (matching the described strategy):
1. Moving average cross: 3-EMA vs 10-EMA must have recently crossed.
2. Vortex indicator: +VI/-VI lines must have recently crossed, same direction.
3. MACD: histogram must have recently flipped sign, same direction — and not
   too many candles ago (a stale flip means the move may already be over).
4. All three must agree AND all three must be "fresh" (crossed within the
   last couple of candles), or no signal.
5. Skip if volatility (ATR) is unusually high right now.
6. Skip if the current candle is a strong candle fighting the trade direction.
"""

import numpy as np
import pandas as pd

from indicators import calc_ema, calc_macd, calc_atr
from config import (
    SCALP_EMA_FAST, SCALP_EMA_SLOW, SCALP_VORTEX_PERIOD,
    SCALP_MACD_FAST, SCALP_MACD_SLOW, SCALP_MACD_SIGNAL,
    SCALP_MAX_BARS_SINCE_CROSS, SCALP_ATR_VOLATILITY_MULT,
)


def calc_vortex(df: pd.DataFrame, period: int = 10):
    high, low, close = df["high"], df["low"], df["close"]
    vm_plus = (high - low.shift(1)).abs()
    vm_minus = (low - high.shift(1)).abs()
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    vi_plus = vm_plus.rolling(period).sum() / tr.rolling(period).sum()
    vi_minus = vm_minus.rolling(period).sum() / tr.rolling(period).sum()
    return vi_plus, vi_minus


def _bars_since_sign_change(sign_series: pd.Series, max_lookback: int = 10):
    n = len(sign_series)
    for i in range(1, min(max_lookback, n) + 1):
        idx = n - 1 - i
        if idx < 0:
            break
        if sign_series.iloc[n - i] != sign_series.iloc[idx]:
            return i - 1
    return None


def evaluate_scalp_signal(df: pd.DataFrame) -> dict:
    close = df["close"]

    ema_f = calc_ema(close, SCALP_EMA_FAST)
    ema_s = calc_ema(close, SCALP_EMA_SLOW)
    ma_sign = np.sign(ema_f - ema_s)
    ma_direction = int(ma_sign.iloc[-1]) if not pd.isna(ma_sign.iloc[-1]) else 0
    ma_bars_since = _bars_since_sign_change(ma_sign)
    ma_fresh = ma_bars_since is not None and ma_bars_since <= SCALP_MAX_BARS_SINCE_CROSS

    vi_plus, vi_minus = calc_vortex(df, SCALP_VORTEX_PERIOD)
    vortex_sign = np.sign(vi_plus - vi_minus)
    vortex_direction = int(vortex_sign.iloc[-1]) if not pd.isna(vortex_sign.iloc[-1]) else 0
    vortex_bars_since = _bars_since_sign_change(vortex_sign)
    vortex_fresh = vortex_bars_since is not None and vortex_bars_since <= SCALP_MAX_BARS_SINCE_CROSS

    macd_line, signal_line, hist = calc_macd(close, SCALP_MACD_FAST, SCALP_MACD_SLOW, SCALP_MACD_SIGNAL)
    hist_sign = np.sign(hist)
    macd_direction = int(hist_sign.iloc[-1]) if not pd.isna(hist_sign.iloc[-1]) else 0
    macd_bars_since = _bars_since_sign_change(hist_sign)
    macd_fresh = macd_bars_since is not None and macd_bars_since <= SCALP_MAX_BARS_SINCE_CROSS

    atr = calc_atr(df)
    atr_avg = atr.rolling(20).mean()
    high_volatility = (
        not pd.isna(atr.iloc[-1]) and not pd.isna(atr_avg.iloc[-1])
        and atr.iloc[-1] > SCALP_ATR_VOLATILITY_MULT * atr_avg.iloc[-1]
    )

    o, h, l, c = df["open"].iloc[-1], df["high"].iloc[-1], df["low"].iloc[-1], df["close"].iloc[-1]
    body = abs(c - o)
    rng = (h - l) if h != l else 1e-9
    candle_dir = 1 if c > o else (-1 if c < o else 0)
    strong_opposing_candle = (body / rng) > 0.6 and candle_dir == -ma_direction

    final_signal = "NO SIGNAL"
    direction = 0

    all_agree = (ma_direction == vortex_direction == macd_direction) and ma_direction != 0
    all_fresh = ma_fresh and vortex_fresh and macd_fresh

    if all_agree and all_fresh and not high_volatility and not strong_opposing_candle:
        direction = ma_direction
        final_signal = "CALL (BUY)" if direction == 1 else "PUT (SELL)"

    return {
        "final_signal": final_signal,
        "direction": direction,
        "ma_direction": ma_direction,
        "vortex_direction": vortex_direction,
        "macd_direction": macd_direction,
        "high_volatility": bool(high_volatility),
  }
