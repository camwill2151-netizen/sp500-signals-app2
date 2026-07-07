from datetime import datetime, timezone
from typing import List

import numpy as np
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from py_vollib.black_scholes.greeks.analytical import (
    delta, gamma, theta, vega, rho
)

app = FastAPI(title="SP500 Signals API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]


def get_risk_free_rate() -> float:
    try:
        tnx = yf.Ticker("^TNX")
        hist = tnx.history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1]) / 100.0
    except Exception:
        pass
    return 0.045


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


def compute_greeks_row(flag: str, S: float, K: float, t: float, r: float, sigma: float) -> dict:
    if t <= 0 or sigma <= 0:
        return {"delta": None, "gamma": None, "theta": None, "vega": None, "rho": None}
    try:
        return {
            "delta": round(delta(flag, S, K, t, r, sigma), 4),
            "gamma": round(gamma(flag, S, K, t, r, sigma), 4),
            "theta": round(theta(flag, S, K, t, r, sigma), 4),
            "vega":  round(vega(flag, S, K, t, r, sigma), 4),
            "rho":   round(rho(flag, S, K, t, r, sigma), 4),
        }
    except Exception:
        return {"delta": None, "gamma": None, "theta": None, "vega": None, "rho": None}


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
                rows.append({"symbol": symbol, "action": "HOLD", "score": 0.50, "price": None, "timestamp": now, "error": "No price data"})
                continue
            action, score = compute_signal(closes)
            rows.append({"symbol": symbol, "action": action, "score": score, "price": round(closes[-1], 2), "timestamp": now})
        except Exception as e:
            rows.append({"symbol": symbol, "action": "HOLD", "score": 0.50, "price": None, "timestamp": now, "error": str(e)})
    return {"count": len(rows), "signals": rows, "generated_at": now}


@app.get("/options")
def options(ticker: str = "AAPL", expiry_index: int = 0, num_strikes: int = 5):
    now = datetime.now(timezone.utc).isoformat()
    r = get_risk_free_rate()
    try:
        tk = yf.Ticker(ticker.upper())
        exps = tk.options
        if not exps:
            raise HTTPException(status_code=404, detail=f"No options found for {ticker}")

        expiry_index = max(0, min(expiry_index, len(exps) - 1))
        expiry = exps[expiry_index]

        hist = tk.history(period="1d")
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No price data for {ticker}")
        S = float(hist["Close"].iloc[-1])

        exp_dt = datetime.strptime(expiry, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        # Floor at 1 day to avoid division by zero in Black-Scholes when expiry is today
        t = max((exp_dt - datetime.now(timezone.utc)).days / 365.0, 1 / 365)

        chain = tk.option_chain(expiry)

        def _safe_int(value) -> int:
            """Convert a potentially NaN numeric value to int, defaulting to 0."""
            if value is None or (isinstance(value, float) and np.isnan(value)):
                return 0
            return int(value)

        def process(df, flag):
            df = df.copy()
            df["dist"] = (df["strike"] - S).abs()
            df = df.nsmallest(num_strikes * 2, "dist").reset_index(drop=True)
            rows = []
            for _, row in df.iterrows():
                K = float(row["strike"])
                iv_raw = float(row["impliedVolatility"])
                iv = iv_raw if iv_raw > 0 else None
                greeks = compute_greeks_row(flag, S, K, t, r, iv) if iv else {"delta": None, "gamma": None, "theta": None, "vega": None, "rho": None}
                rows.append({
                    "contract": row.get("contractSymbol", ""),
                    "type": "call" if flag == "c" else "put",
                    "strike": K,
                    "last": round(float(row["lastPrice"]), 4),
                    "bid": round(float(row["bid"]), 4),
                    "ask": round(float(row["ask"]), 4),
                    "impliedVolatility": round(iv_raw, 4),
                    "volume": _safe_int(row["volume"]),
                    "openInterest": _safe_int(row["openInterest"]),
                    **greeks,
                })
            return rows

        calls = process(chain.calls, "c")
        puts = process(chain.puts, "p")

        return {
            "ticker": ticker.upper(),
            "spot": round(S, 2),
            "expiry": expiry,
            "t_years": round(t, 4),
            "risk_free_rate": round(r, 4),
            "calls": calls,
            "puts": puts,
            "generated_at": now,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
