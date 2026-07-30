"""
Entry point. Runs ONE scan pass over all configured pairs, then exits.

Runs TWO independent strategies per pair, both using the M1 data already
fetched (no extra API cost for either):
  1. EMA/Vortex/MACD scalp confluence (M1 candles, 1-min expiry)
  2. MA(100)/ZigZag/SuperTrend/RSI confluence (M1 candles, 3-min expiry)

The earlier price-action/market-structure strategy has been removed —
it's no longer called here.

Either strategy firing sends its own labeled Discord alert.

Triggered on a schedule by GitHub Actions (every 30 minutes).
Local test run: python main.py
"""

import traceback

from config import PAIRS, TIMEFRAMES
from data_fetcher import fetch_multi_timeframe
from scalp_strategy import evaluate_scalp_signal
from trend_supertrend_strategy import evaluate_trend_supertrend_signal
from discord_alert import send_discord_message, format_scalp_message, format_trend_supertrend_message


def scan_once():
    for pair in PAIRS:
        try:
            tf_data = fetch_multi_timeframe(pair, TIMEFRAMES)
            m1_df = tf_data["trigger"]

            # --- Strategy 1: EMA/Vortex/MACD scalp (1-min expiry) ---
            scalp_result = evaluate_scalp_signal(m1_df)
            print(f"{pair:10s} [scalp] ma={scalp_result['ma_direction']:+d} "
                  f"vortex={scalp_result['vortex_direction']:+d} "
                  f"macd={scalp_result['macd_direction']:+d} "
                  f"-> {scalp_result['final_signal']}")

            if scalp_result["direction"] != 0:
                send_discord_message(format_scalp_message(pair, scalp_result))

            # --- Strategy 2: MA/ZigZag/SuperTrend/RSI (3-min expiry) ---
            trend_result = evaluate_trend_supertrend_signal(m1_df)
            print(f"{pair:10s} [trend]  ma={trend_result['ma_dir']:+d} "
                  f"zigzag={trend_result['zigzag_dir']:+d} "
                  f"supertrend={trend_result['supertrend_dir']:+d} "
                  f"rsi={trend_result['rsi_dir']:+d} "
                  f"-> {trend_result['final_signal']}")

            if trend_result["direction"] != 0:
                send_discord_message(format_trend_supertrend_message(pair, trend_result))

        except Exception as e:
            print(f"[error] {pair}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    scan_once()
    
