from typing import Dict, List, Optional
import math
import pandas as pd
import yfinance as yf

from .futures_greeks import build_futures_greeks


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.dropna()
    return float(val.iloc[-1]) if not val.empty else 50.0


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _macd(series: pd.Series) -> Dict[str, float]:
    ema12 = _ema(series, 12)
    ema26 = _ema(series, 26)
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return {
        "macd": float(macd.iloc[-1]),
        "macd_signal": float(signal.iloc[-1]),
        "macd_hist": float(hist.iloc[-1]),
    }


def _trend_score(close: pd.Series) -> Dict[str, float]:
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    last = float(close.iloc[-1])
    s20 = float(sma20.iloc[-1]) if not sma20.dropna().empty else last
    s50 = float(sma50.iloc[-1]) if not sma50.dropna().empty else last
    r = _rsi(close, 14)
    m = _macd(close)

    score = 0.0
    # Trend
    if last > s20: score += 1
    else: score -= 1
    if s20 > s50: score += 1
    else: score -= 1

    # Momentum
    if r < 30: score += 1
    elif r > 70: score -= 1

    if m["macd_hist"] > 0: score += 1
    else: score -= 1

    return {
        "tech_score": score, "last": last, "sma20": s20, "sma50": s50,
        "rsi14": r, "macd": m["macd"], "macd_signal": m["macd_signal"], "macd_hist": m["macd_hist"]
    }


def _fundamental_score(ticker: str) -> Dict[str, float]:
    # Lightweight and robust with yfinance info fields (can be sparse)
    t = yf.Ticker(ticker)
    info = getattr(t, "info", {}) or {}

    pe = info.get("trailingPE")
    eps_g = info.get("earningsGrowth")
    rev_g = info.get("revenueGrowth")
    margin = info.get("profitMargins")
    de = info.get("debtToEquity")

    score = 0.0

    if isinstance(pe, (int, float)):
        if pe > 0 and pe < 25: score += 1
        elif pe > 60: score -= 1

    if isinstance(eps_g, (int, float)):
        score += 1 if eps_g > 0 else -1

    if isinstance(rev_g, (int, float)):
        score += 1 if rev_g > 0 else -1

    if isinstance(margin, (int, float)):
        score += 1 if margin > 0.10 else -1

    if isinstance(de, (int, float)):
        score += 1 if de < 100 else -1

    return {
        "fund_score": score,
        "trailingPE": pe, "earningsGrowth": eps_g, "revenueGrowth": rev_g,
        "profitMargins": margin, "debtToEquity": de
    }


def _signal_from_scores(option_type: str, tech_score: float, fund_score: float, delta: Optional[float], theta: Optional[float]) -> str:
    # Combined directional score
    base = tech_score + 0.7 * fund_score

    # Option-type direction mapping
    if option_type == "call":
        directional = base
    else:
        directional = -base

    # Greeks tilt
    if delta is not None:
        directional += 0.5 * abs(delta)
    if theta is not None:
        directional -= 0.1 * max(theta, 0)  # penalize positive theta for buyer profile if present

    if directional >= 1.5:
        return "BUY"
    if directional <= -1.5:
        return "SELL"
    return "HOLD"


def generate_option_signals(
    tickers: List[str],
    r: float = 0.05,
    q: float = 0.00,
    t_days: int = 30,
    sigma: float = 0.20,
) -> List[Dict]:
    T = max(1, t_days) / 365.0
    greeks_rows = build_futures_greeks(
        tickers=tickers,
        r=r, q=q, T=T, sigma=sigma,
        moneyness_steps=[-0.05, 0.0, 0.05],
        option_types=["call", "put"],
    )

    by_ticker = {}
    for tk in tickers:
        hist = yf.Ticker(tk).history(period="6mo", interval="1d")
        if hist is None or hist.empty or "Close" not in hist:
            by_ticker[tk] = None
        else:
            by_ticker[tk] = hist["Close"].dropna()

    out = []
    for row in greeks_rows:
        tk = row["ticker"]
        close = by_ticker.get(tk)

        if close is None or len(close) < 60:
            continue

        tech = _trend_score(close)
        fund = _fundamental_score(tk)

        sig = _signal_from_scores(
            option_type=row["option_type"],
            tech_score=tech["tech_score"],
            fund_score=fund["fund_score"],
            delta=row.get("delta"),
            theta=row.get("theta"),
        )

        out.append({
            **row,
            **tech,
            **fund,
            "signal": sig
        })

    return out
