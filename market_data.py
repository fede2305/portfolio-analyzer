"""Fetch market data from yfinance for a list of tickers.

Usage:
    python market_data.py AAPL MSFT GOOGL
    echo '["AAPL","MSFT"]' | python market_data.py --stdin

Output JSON to stdout: per-ticker last price, 52w high/low, ATH, MAs,
RSI(14), distance to ATH and 52w high.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import yfinance as yf


def rsi(series, period: int = 14) -> float | None:
    if len(series) < period + 1:
        return None
    delta = series.diff().dropna()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean().iloc[-1]
    avg_loss = loss.rolling(period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def analyze(ticker: str) -> dict[str, Any]:
    try:
        t = yf.Ticker(ticker)
        hist_max = t.history(period="max", auto_adjust=True)
        if hist_max.empty:
            return {"ticker": ticker, "error": "no data"}
        close = hist_max["Close"]
        last = float(close.iloc[-1])
        ath = float(close.max())
        ath_date = close.idxmax().strftime("%Y-%m-%d")

        hist_1y = hist_max.tail(252)
        high_52w = float(hist_1y["High"].max())
        low_52w = float(hist_1y["Low"].min())

        ma50 = float(close.tail(50).mean()) if len(close) >= 50 else None
        ma200 = float(close.tail(200).mean()) if len(close) >= 200 else None
        rsi14 = rsi(close)

        vol_30d = float(hist_max["Volume"].tail(30).mean())
        vol_90d = float(hist_max["Volume"].tail(90).mean())

        return {
            "ticker": ticker,
            "last_price": last,
            "currency": (t.fast_info.get("currency") if hasattr(t, "fast_info") else None),
            "ath": ath,
            "ath_date": ath_date,
            "pct_from_ath": round((last / ath - 1) * 100, 2),
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pct_from_52w_high": round((last / high_52w - 1) * 100, 2),
            "ma50": ma50,
            "ma200": ma200,
            "ma50_above_ma200": (ma50 is not None and ma200 is not None and ma50 > ma200),
            "rsi14": rsi14,
            "vol_30d_avg": vol_30d,
            "vol_90d_avg": vol_90d,
            "vol_accumulation": vol_30d > vol_90d,
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--stdin":
        tickers = json.load(sys.stdin)
    elif args:
        tickers = args
    else:
        print("usage: market_data.py TICKER [TICKER ...]  or  --stdin (JSON array)", file=sys.stderr)
        sys.exit(2)

    results = [analyze(t.upper()) for t in tickers]
    json.dump(results, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
