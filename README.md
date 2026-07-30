# Multi-Indicator Confluence Signal Bot

15 indicators across trend, momentum, volatility, volume, and price action,
combined into a weighted confluence score, checked across 3 timeframes
(H1 trend bias → M5 entry signal → M1 trigger confirmation).

**Signal requirement:** at least 11 of 15 indicators must agree on direction,
AND the weighted confluence score must clear 75%, AND the trigger timeframe
must not be fighting the trade — all three, every time. Signals also come
with a strength label (MODERATE / STRONG / VERY STRONG) based on how many
indicators agreed.

## Indicators included

| Category | Indicators |
|---|---|
| Trend | EMA 9/21/50 stack, ADX, MACD, Ichimoku Cloud |
| Momentum | RSI, Stochastic RSI, CCI, Williams %R |
| Volatility | Bollinger Bands, Keltner squeeze |
| Volume | OBV, VWAP |
| Price action | Candle patterns, Support/Resistance, Fibonacci retracement |

## How it runs

This bot does **not** run as a persistent always-on process. Instead, GitHub
Actions triggers it on a schedule — every 5 minutes it wakes up, checks all
configured pairs, sends a Discord message if a signal fires, then exits.
No server to keep alive, no "sleeping" free tier to fight with.

## Setup

1. **Twelve Data API key** (free): sign up at https://twelvedata.com/
2. **Discord webhook**: in your Discord server, go to your channel →
   Edit Channel → Integrations → Webhooks → New Webhook → Copy Webhook URL
3. **Push this folder to a new GitHub repo** (make it public — see note below on why)
4. **Add secrets** in your repo: Settings → Secrets and variables → Actions → New repository secret
   - `TWELVE_DATA_API_KEY`
   - `DISCORD_WEBHOOK_URL`
5. That's it — the workflow in `.github/workflows/scan.yml` starts running
   automatically every 5 minutes once it's pushed. You can also trigger it
   manually from the repo's "Actions" tab (workflow_dispatch).

### Why public repo?

GitHub Actions free tier gives 2,000 minutes/month for private repos, but
**unlimited minutes for public repos**. Running every 5 minutes uses more
than the private free allowance. Your code itself has no secrets in it
(those live safely in GitHub Secrets, never in the files), so making the
repo public is safe.

## Testing locally before deploying

```
pip install -r requirements.txt
export TWELVE_DATA_API_KEY="your_key"
export DISCORD_WEBHOOK_URL="your_webhook_url"
python main.py
```

## Tuning

Everything lives in `config.py`:
- `PAIRS` — which markets to scan
- `WEIGHTS` — how much each indicator counts toward the confluence score
- `SIGNAL_THRESHOLD` — currently 0.75 (strict)
- `MIN_INDICATORS_AGREE` — currently 11 of 15
- `STRENGTH_BANDS` — thresholds for MODERATE/STRONG/VERY STRONG labels
- `ADX_TREND_MINIMUM` — below this, market is considered too choppy to trust trend indicators

## Being straight with you about accuracy

No combination of indicators — 6 or 15 or 50 — gives a real edge above what
the underlying market volatility allows, especially on short binary options
timeframes. Requiring 11/15 agreement means far fewer signals than a loose
system, but "fewer and stricter" is not the same as "guaranteed right."

Before trusting this with real money:
1. **Paper trade it** for at least 1-2 weeks — track real signals against
   real outcomes on your actual pairs.
2. Expect roughly 2-3 signals/day across 7 pairs on average, some days zero,
   occasional high-volatility days more — this is normal, not a malfunction.
3. Treat any indicator-based system on short timeframes as inherently
   high-variance — size positions accordingly.
4. This only works for real-market pairs (regular forex/crypto during real
   trading hours), not OTC pairs — OTC price feeds are broker-generated and
   have no public data source, so no external tool can see them.
