"""
Configuration for the Multi-Strategy Signal Bot.

Strategy 1 (scalp_strategy.py): EMA(3/10) + Vortex(10) + MACD(15,27,9)
confluence, on M1 candles, 1-minute expiry.

Strategy 2 (trend_supertrend_strategy.py): MA(100) trend filter + ZigZag
+ SuperTrend(10,1) + RSI(10) confluence, on M1 candles, 3-minute expiry.

Edit the values below — no other file needs touching for basic setup.
"""

import os

# ---------------------------------------------------------------
# API CREDENTIALS
# ---------------------------------------------------------------
# Twelve Data free tier: https://twelvedata.com/ (800 req/day free)
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "YOUR_TWELVE_DATA_KEY")

# Discord webhook
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "YOUR_WEBHOOK_URL")

# Telegram bot — see README for how to create one via @BotFather.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

# ---------------------------------------------------------------
# MARKETS TO SCAN
# ---------------------------------------------------------------
PAIRS = [
    "CAD/JPY", "EUR/JPY", "CAD/CHF",
    "EUR/AUD", "GBP/JPY",
]

TIMEFRAMES = {
    "trend": "1h",
    "signal": "5min",
    "trigger": "1min",
}

CANDLE_LOOKBACK = 150

# ---------------------------------------------------------------
# MARKET STRUCTURE SETTINGS (used by trend_supertrend_strategy.py's ZigZag)
# ---------------------------------------------------------------
SWING_WINDOW = 3
SWING_LOOKBACK = 60
STRUCTURE_PROXIMITY_PCT = 0.0025

# ---------------------------------------------------------------
# SCALP STRATEGY SETTINGS (EMA/Vortex/MACD on M1)
# ---------------------------------------------------------------
SCALP_EMA_FAST = 3
SCALP_EMA_SLOW = 10
SCALP_VORTEX_PERIOD = 10
SCALP_MACD_FAST = 15
SCALP_MACD_SLOW = 27
SCALP_MACD_SIGNAL = 9
SCALP_MAX_BARS_SINCE_CROSS = 2
SCALP_ATR_VOLATILITY_MULT = 1.5

# ---------------------------------------------------------------
# TREND/SUPERTREND STRATEGY SETTINGS (M1, 3-min expiry)
# ---------------------------------------------------------------
TREND_MA_PERIOD = 100
ZIGZAG_WINDOW = 3
ZIGZAG_LOOKBACK = 60
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 1.0
TREND_RSI_PERIOD = 10
SUPERTREND_FRESH_BARS = 2
RSI_OVEREXTEND_BARS = 5
TREND_ATR_VOLATILITY_MULT = 1.5

# Scan interval is controlled by .github/workflows/scan.yml (currently every
# 30 minutes). With 5 pairs x 3 timeframes = 15 requests/scan, that's 720
# requests/day — comfortably under Twelve Data's free 800/day limit.
SCAN_INTERVAL_SECONDS = 1800

# Seconds to wait between individual API calls within one scan, so a single
# run never exceeds the free tier's 8-requests-per-minute cap.
API_CALL_DELAY_SECONDS = 8
