"""
Combines all 15 indicators into a single weighted confluence score,
then requires agreement across three timeframes before firing a signal.

This mirrors the Grandmaster approach (H1 = trend bias, M5 = entry signal,
M1 = fine trigger) but with a broader, weighted indicator set instead of
a flat 6-factor vote.
"""

import pandas as pd

from config import (
    WEIGHTS, SIGNAL_THRESHOLD, ADX_TREND_MINIMUM,
    MIN_INDICATORS_AGREE, STRENGTH_BANDS,
)
import indicators as ind


INDICATOR_FUNCS = {
    "ema_cross":          ind.signal_ema_cross,
    "adx_trend":          lambda df: ind.signal_adx_trend(df, ADX_TREND_MINIMUM),
    "macd":               ind.signal_macd,
    "ichimoku":           ind.signal_ichimoku,
    "rsi":                ind.signal_rsi,
    "stoch_rsi":          ind.signal_stoch_rsi,
    "cci":                ind.signal_cci,
    "williams_r":         ind.signal_williams_r,
    "bollinger":          ind.signal_bollinger,
    "keltner_squeeze":    ind.signal_keltner_squeeze,
    "obv":                ind.signal_obv,
    "vwap":               ind.signal_vwap,
    "candle_pattern":     ind.signal_candle_pattern,
    "support_resistance": ind.signal_support_resistance,
    "fibonacci":          ind.signal_fibonacci,
}


def strength_label(agree_count: int) -> str:
    for min_count, label in STRENGTH_BANDS:
        if agree_count >= min_count:
            return label
    return "WEAK"


def score_timeframe(df: pd.DataFrame) -> dict:
    """
    Runs every indicator on one timeframe's DataFrame.
    Returns {"votes": {name: -1/0/1}, "score": float in [-1, 1]}
    """
    votes = {}
    for name, func in INDICATOR_FUNCS.items():
        try:
            votes[name] = func(df)
        except Exception:
            votes[name] = 0  # fail-safe: missing data shouldn't crash the scan

    max_weight = sum(WEIGHTS.values())
    weighted_sum = sum(votes[name] * WEIGHTS[name] for name in votes)
    score = weighted_sum / max_weight  # normalized to [-1, 1]

    return {"votes": votes, "score": score}


def evaluate_pair(timeframe_data: dict) -> dict:
    """
    timeframe_data: {"trend": df, "signal": df, "trigger": df}

    Logic:
    1. Score each timeframe independently.
    2. The 'trend' (H1) timeframe sets the allowed direction — it acts as a filter.
    3. The 'signal' (M5) timeframe's score must clear SIGNAL_THRESHOLD in the
       same direction as trend.
    4. The 'trigger' (M1) timeframe must not be sharply against the trade
       (final confirmation, catches the trade closer to entry price).

    Returns a dict describing the final decision, plus per-timeframe detail
    so you can log/debug why a signal did or didn't fire.
    """
    trend_result = score_timeframe(timeframe_data["trend"])
    signal_result = score_timeframe(timeframe_data["signal"])
    trigger_result = score_timeframe(timeframe_data["trigger"])

    trend_dir = 1 if trend_result["score"] > 0.15 else (-1 if trend_result["score"] < -0.15 else 0)

    final_signal = "NO SIGNAL"
    direction = 0
    agree_count = 0
    strength = None

    if trend_dir != 0:
        votes = signal_result["votes"]
        agree_count = sum(1 for v in votes.values() if v == trend_dir)

        signal_aligned = (
            (trend_dir == 1 and signal_result["score"] >= SIGNAL_THRESHOLD) or
            (trend_dir == -1 and signal_result["score"] <= -SIGNAL_THRESHOLD)
        )
        trigger_not_opposed = (
            (trend_dir == 1 and trigger_result["score"] > -0.2) or
            (trend_dir == -1 and trigger_result["score"] < 0.2)
        )
        enough_indicators_agree = agree_count >= MIN_INDICATORS_AGREE

        if signal_aligned and trigger_not_opposed and enough_indicators_agree:
            direction = trend_dir
            final_signal = "CALL (BUY)" if trend_dir == 1 else "PUT (SELL)"
            strength = strength_label(agree_count)

    return {
        "final_signal": final_signal,
        "direction": direction,
        "agree_count": agree_count,
        "strength": strength,
        "trend": trend_result,
        "signal": signal_result,
        "trigger": trigger_result,
      }
