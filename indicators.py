"""
Manual implementations of all indicators — no external TA library required,
so this runs anywhere pandas/numpy runs (including free Render tiers).

Every `signal_*` function returns one of: 1 (bullish), -1 (bearish), 0 (neutral).
Every `calc_*` function returns the raw indicator series/value for display/logging.
"""

import numpy as np
import pandas as pd


# =================================================================
# TREND INDICATORS
# =================================================================

def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def signal_ema_cross(df: pd.DataFrame) -> int:
    """EMA 9/21/50 stacked alignment."""
    ema9 = calc_ema(df["close"], 9)
    ema21 = calc_ema(df["close"], 21)
    ema50 = calc_ema(df["close"], 50)
    if ema9.iloc[-1] > ema21.iloc[-1] > ema50.iloc[-1]:
        return 1
    if ema9.iloc[-1] < ema21.iloc[-1] < ema50.iloc[-1]:
        return -1
    return 0


def calc_adx(df: pd.DataFrame, period: int = 14):
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    plus_dm[(plus_dm - minus_dm) <= 0] = 0
    minus_dm[(minus_dm - plus_dm) <= 0] = 0

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx, plus_di, minus_di


def signal_adx_trend(df: pd.DataFrame, minimum: float = 20) -> int:
    adx, plus_di, minus_di = calc_adx(df)
    last_adx, last_plus, last_minus = adx.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]
    if pd.isna(last_adx) or pd.isna(last_plus) or pd.isna(last_minus):
        return 0  # not enough history yet — don't guess
    if last_adx < minimum:
        return 0  # market not trending strongly enough to trust
    return 1 if last_plus > last_minus else -1


def calc_macd(series: pd.Series, fast=12, slow=26, signal=9):
    macd_line = calc_ema(series, fast) - calc_ema(series, slow)
    signal_line = calc_ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def signal_macd(df: pd.DataFrame) -> int:
    macd_line, signal_line, hist = calc_macd(df["close"])
    if hist.iloc[-1] > 0 and hist.iloc[-2] <= 0:
        return 1
    if hist.iloc[-1] < 0 and hist.iloc[-2] >= 0:
        return -1
    return 1 if hist.iloc[-1] > 0 else (-1 if hist.iloc[-1] < 0 else 0)


def calc_ichimoku(df: pd.DataFrame):
    high, low = df["high"], df["low"]
    conv = (high.rolling(9).max() + low.rolling(9).min()) / 2
    base = (high.rolling(26).max() + low.rolling(26).min()) / 2
    span_a = ((conv + base) / 2).shift(26)
    span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    return conv, base, span_a, span_b


def signal_ichimoku(df: pd.DataFrame) -> int:
    conv, base, span_a, span_b = calc_ichimoku(df)
    price = df["close"].iloc[-1]
    cloud_top = max(span_a.iloc[-1], span_b.iloc[-1])
    cloud_bottom = min(span_a.iloc[-1], span_b.iloc[-1])
    if price > cloud_top and conv.iloc[-1] > base.iloc[-1]:
        return 1
    if price < cloud_bottom and conv.iloc[-1] < base.iloc[-1]:
        return -1
    return 0


# =================================================================
# MOMENTUM INDICATORS
# =================================================================

def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def signal_rsi(df: pd.DataFrame) -> int:
    rsi = calc_rsi(df["close"])
    val = rsi.iloc[-1]
    if val < 30:
        return 1  # oversold -> bullish reversal bias
    if val > 70:
        return -1
    return 0


def calc_stoch_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    rsi = calc_rsi(series, period)
    min_rsi = rsi.rolling(period).min()
    max_rsi = rsi.rolling(period).max()
    return 100 * (rsi - min_rsi) / (max_rsi - min_rsi).replace(0, np.nan)


def signal_stoch_rsi(df: pd.DataFrame) -> int:
    stoch = calc_stoch_rsi(df["close"])
    val = stoch.iloc[-1]
    if val < 20:
        return 1
    if val > 80:
        return -1
    return 0


def calc_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(period).mean()
    mean_dev = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma) / (0.015 * mean_dev.replace(0, np.nan))


def signal_cci(df: pd.DataFrame) -> int:
    val = calc_cci(df).iloc[-1]
    if val < -100:
        return 1
    if val > 100:
        return -1
    return 0


def calc_williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    highest_high = df["high"].rolling(period).max()
    lowest_low = df["low"].rolling(period).min()
    return -100 * (highest_high - df["close"]) / (highest_high - lowest_low).replace(0, np.nan)


def signal_williams_r(df: pd.DataFrame) -> int:
    val = calc_williams_r(df).iloc[-1]
    if val < -80:
        return 1
    if val > -20:
        return -1
    return 0


# =================================================================
# VOLATILITY INDICATORS
# =================================================================

def calc_bollinger(series: pd.Series, period: int = 20, std_mult: float = 2.0):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


def signal_bollinger(df: pd.DataFrame) -> int:
    upper, mid, lower = calc_bollinger(df["close"])
    price = df["close"].iloc[-1]
    if price <= lower.iloc[-1]:
        return 1  # touching/below lower band -> bounce potential
    if price >= upper.iloc[-1]:
        return -1
    return 0


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def calc_keltner(df: pd.DataFrame, period: int = 20, atr_mult: float = 1.5):
    mid = calc_ema(df["close"], period)
    atr = calc_atr(df, period)
    upper = mid + atr_mult * atr
    lower = mid - atr_mult * atr
    return upper, mid, lower


def signal_keltner_squeeze(df: pd.DataFrame) -> int:
    """
    Detects a BB-inside-Keltner 'squeeze' (low volatility, breakout pending)
    and gives directional bias once price breaks a channel edge.
    """
    bb_upper, bb_mid, bb_lower = calc_bollinger(df["close"])
    k_upper, k_mid, k_lower = calc_keltner(df)
    price = df["close"].iloc[-1]

    squeeze_on = bb_upper.iloc[-1] < k_upper.iloc[-1] and bb_lower.iloc[-1] > k_lower.iloc[-1]
    if not squeeze_on:
        return 0
    if price > k_mid.iloc[-1]:
        return 1
    if price < k_mid.iloc[-1]:
        return -1
    return 0


# =================================================================
# VOLUME INDICATORS
# =================================================================

def calc_obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff()).fillna(0)
    return (direction * df["volume"]).cumsum()


def signal_obv(df: pd.DataFrame) -> int:
    obv = calc_obv(df)
    obv_ema = calc_ema(obv, 20)
    last_obv, last_ema = obv.iloc[-1], obv_ema.iloc[-1]
    prev_obv, prev_ema = obv.iloc[-2], obv_ema.iloc[-2]
    if pd.isna(last_obv) or pd.isna(last_ema) or pd.isna(prev_obv) or pd.isna(prev_ema):
        return 0
    if last_obv > last_ema and prev_obv <= prev_ema:
        return 1
    if last_obv < last_ema and prev_obv >= prev_ema:
        return -1
    return 1 if last_obv > last_ema else -1


def calc_vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    return (tp * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, np.nan)


def signal_vwap(df: pd.DataFrame) -> int:
    vwap = calc_vwap(df)
    price = df["close"].iloc[-1]
    if price > vwap.iloc[-1]:
        return 1
    if price < vwap.iloc[-1]:
        return -1
    return 0


# =================================================================
# PRICE ACTION: CANDLE PATTERNS
# =================================================================

def signal_candle_pattern(df: pd.DataFrame) -> int:
    """
    Checks the most recent 1-2 candles for common reversal/continuation patterns.
    Returns the strongest pattern found, bullish or bearish.
    """
    if len(df) < 3:
        return 0

    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    rng = (h - l).replace(0, np.nan)

    i = -1  # last candle

    # Bullish engulfing
    if (c.iloc[i-1] < o.iloc[i-1]) and (c.iloc[i] > o.iloc[i]) and \
       (c.iloc[i] >= o.iloc[i-1]) and (o.iloc[i] <= c.iloc[i-1]):
        return 1

    # Bearish engulfing
    if (c.iloc[i-1] > o.iloc[i-1]) and (c.iloc[i] < o.iloc[i]) and \
       (o.iloc[i] >= c.iloc[i-1]) and (c.iloc[i] <= o.iloc[i-1]):
        return -1

    # Hammer / bullish pin bar (long lower wick, small body near top)
    lower_wick = np.minimum(o.iloc[i], c.iloc[i]) - l.iloc[i]
    upper_wick = h.iloc[i] - np.maximum(o.iloc[i], c.iloc[i])
    if rng.iloc[i] and body.iloc[i] / rng.iloc[i] < 0.35 and lower_wick > 2 * body.iloc[i]:
        return 1

    # Shooting star / bearish pin bar (long upper wick)
    if rng.iloc[i] and body.iloc[i] / rng.iloc[i] < 0.35 and upper_wick > 2 * body.iloc[i]:
        return -1

    # Doji (indecision) — treated as neutral, but flagged separately if needed
    if rng.iloc[i] and body.iloc[i] / rng.iloc[i] < 0.1:
        return 0

    return 0


# =================================================================
# PRICE ACTION: SUPPORT/RESISTANCE + FIBONACCI
# =================================================================

def find_swing_levels(df: pd.DataFrame, lookback: int = 40, window: int = 3):
    """Simple fractal-based swing high/low detector."""
    highs, lows = [], []
    h, l = df["high"], df["low"]
    recent = df.iloc[-lookback:]
    for i in range(window, len(recent) - window):
        idx = recent.index[i]
        seg_h = recent["high"].iloc[i-window:i+window+1]
        seg_l = recent["low"].iloc[i-window:i+window+1]
        if recent["high"].iloc[i] == seg_h.max():
            highs.append(recent["high"].iloc[i])
        if recent["low"].iloc[i] == seg_l.min():
            lows.append(recent["low"].iloc[i])
    return highs, lows


def signal_support_resistance(df: pd.DataFrame, proximity_pct: float = 0.0015) -> int:
    highs, lows = find_swing_levels(df)
    price = df["close"].iloc[-1]

    near_resistance = any(abs(price - r) / price < proximity_pct for r in highs)
    near_support = any(abs(price - s) / price < proximity_pct for s in lows)

    if near_support and not near_resistance:
        return 1
    if near_resistance and not near_support:
        return -1
    return 0


def signal_fibonacci(df: pd.DataFrame, lookback: int = 60) -> int:
    """
    Uses the most recent significant swing to build fib retracement levels
    (38.2%, 50%, 61.8%) and checks if price is bouncing off one.
    """
    segment = df.iloc[-lookback:]
    swing_high = segment["high"].max()
    swing_low = segment["low"].min()
    price = df["close"].iloc[-1]
    diff = swing_high - swing_low
    if diff == 0:
        return 0

    trend_up = segment["close"].iloc[-1] > segment["close"].iloc[0]
    levels = [0.382, 0.5, 0.618]

    for lvl in levels:
        fib_price = swing_high - diff * lvl if trend_up else swing_low + diff * lvl
        if abs(price - fib_price) / price < 0.0015:
            return 1 if trend_up else -1
    return 0
