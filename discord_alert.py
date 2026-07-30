import requests
from config import DISCORD_WEBHOOK_URL


def send_discord_message(text: str):
    payload = {"content": text}
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[discord] failed to send message: {e}")


def format_scalp_message(pair: str, result: dict) -> str:
    action = "BUY" if result["direction"] == 1 else "SELL"
    return f"⚡ **{action}** — `{pair}` | Candle: M1 | Expiry: 1 min"


def format_trend_supertrend_message(pair: str, result: dict) -> str:
    action = "BUY" if result["direction"] == 1 else "SELL"
    return f"🎯 **{action}** — `{pair}` | Candle: M1 | Expiry: 3 min"
