from datetime import datetime, timezone
from typing import List

import yfinance as yf
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SP500 Signals API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]


def compute_signal(closes: List[float]):
    if len(closes) < 20:
        return "HOLD", 0.50

    price = closes[-1]
    sma5 = sum(closes[-5:]) / 5
    sma20 = sum(closes[-20:]) / 20

    raw = 0.5 + ((sma5 - sma20) / max(price, 1e-9)) * 8
    score = max(0.0, min(1.0, raw))

    if score >= 0.66:
        action = "BUY"
    elif score <= 0.34:
        action = "SELL"
    else:
        action = "HOLD"
    return action, round(score, 2)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "SP500 Signals API running"}


@app.get("/signals")
def signals(tickers: str = ",".join(DEFAULT_TICKERS), period: str = "3mo"):
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    now = datetime.now(timezone.utc).isoformat()

    rows = []
    for symbol in symbols:
        try:
            hist = yf.Ticker(symbol).history(period=period)
            closes = [float(x) for x in hist["Close"].dropna().tolist()]

            if not closes:
                rows.append(
                    {
                        "symbol": symbol,
                        "action": "HOLD",
                        "score": 0.50,
                        "price": None,
                        "timestamp": now,
                        "error": "No price data",
                    }
                )
                continue

            action, score = compute_signal(closes)
            rows.append(
                {
                    "symbol": symbol,
                    "action": action,
                    "score": score,
                    "price": round(closes[-1], 2),
                    "timestamp": now,
                }
            )
        except Exception as e:
            rows.append(
                {
                    "symbol": symbol,
                    "action": "HOLD",
                    "score": 0.50,
                    "price": None,
                    "timestamp": now,
                    "error": str(e),
                }
            )

    return {"count": len(rows), "signals": rows, "generated_at": now}
