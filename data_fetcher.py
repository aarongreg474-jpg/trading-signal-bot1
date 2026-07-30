"""
Pulls OHLCV candle data from Twelve Data (https://twelvedata.com/).
Free tier: 800 requests/day, 8 requests/minute — plenty for a handful of pairs
scanned once a minute if you stagger calls (see main.py).

If you'd rather use a different data source (Binance/ccxt for crypto-only,
or a broker's own API), only this file needs to change — everything else
just expects a DataFrame with columns: open, high, low, close, volume.
"""

import time
from datetime import datetime, timezone, timedelta
import requests
import pandas as pd

from config import TWELVE_DATA_API_KEY, CANDLE_LOOKBACK, API_CALL_DELAY_SECONDS


INTERVAL_MINUTES = {"1min": 1, "5min": 5, "1h": 60}


BASE_URL = "https://api.twelvedata.com/time_series"


def fetch_candles(symbol: str, interval: str, output_size: int = CANDLE_LOOKBACK) -> pd.DataFrame:
    """
    Fetch candles for one symbol/interval.
    interval examples: '1min', '5min', '1h'
    Returns a DataFrame sorted oldest -> newest, indexed by datetime.
    """
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": output_size,
        "apikey": TWELVE_DATA_API_KEY,
        "format": "JSON",
    }

    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "values" not in data:
        raise RuntimeError(f"Twelve Data error for {symbol} ({interval}): {data}")

    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    if "volume" in df.columns:
        df["volume"] = df["volume"].astype(float)
    else:
        df["volume"] = (df["high"] - df["low"]) * 1_000_000

    df = df.set_index("datetime")

    interval_min = INTERVAL_MINUTES.get(interval)
    if interval_min and len(df) > 0:
        last_candle_time = df.index[-1]
        if last_candle_time.tzinfo is None:
            last_candle_time = last_candle_time.tz_localize("UTC")
        candle_close_time = last_candle_time + timedelta(minutes=interval_min)
        now = datetime.now(timezone.utc)
        if now < candle_close_time:
            df = df.iloc[:-1]

    return df


def fetch_multi_timeframe(symbol: str, timeframes: dict) -> dict:
    """
    timeframes: e.g. {"trend": "1h", "signal": "5min", "trigger": "1min"}
    Returns: {"trend": df, "signal": df, "trigger": df}

    Sleeps briefly between each request so a single scan (which fetches 3
    timeframes per pair) never exceeds the free tier's per-minute rate limit.
    """
    result = {}
    for label, interval in timeframes.items():
        result[label] = fetch_candles(symbol, interval)
        time.sleep(API_CALL_DELAY_SECONDS)
    return result
