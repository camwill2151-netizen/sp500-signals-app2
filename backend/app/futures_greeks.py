import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

import yfinance as yf
import pandas as pd
from scipy.stats import norm


# Map equity ticker -> proxy futures ticker (Yahoo Finance symbols)
# NOTE: These are index futures proxies, not single-stock futures.
FUTURES_PROXY = {
    "SPY": "ES=F", "IVV": "ES=F", "VOO": "ES=F",
    "QQQ": "NQ=F",
    "IWM": "RTY=F",
    "DIA": "YM=F",
    "^GSPC": "ES=F", "^NDX": "NQ=F", "^RUT": "RTY=F", "^DJI": "YM=F",
}

DEFAULT_R = 0.05   # risk-free annualized
DEFAULT_Q = 0.00   # carry/dividend yield annualized
DEFAULT_T = 30/365 # 30D tenor
DEFAULT_SIGMA = 0.20

FALLBACK_SPOTS = {
    "ES=F": 5600.0,
    "NQ=F": 20200.0,
    "RTY=F": 2200.0,
    "YM=F": 41000.0,
}


@dataclass
class GreeksRow:
    ticker: str
    futures_symbol: str
    spot_proxy: float
    strike: float
    t_years: float
    r: float
    q: float
    sigma: float
    option_type: str
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


def _bs_greeks(S: float, K: float, T: float, r: float, q: float, sigma: float, option_type: str):
    # Black-Scholes-Merton (manual) for European options
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return {"price": None, "delta": None, "gamma": None, "theta": None, "vega": None, "rho": None}

    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    Nd1 = norm.cdf(d1)
    Nd2 = norm.cdf(d2)
    Nmd1 = norm.cdf(-d1)
    Nmd2 = norm.cdf(-d2)
    nd1 = norm.pdf(d1)

    disc_q = math.exp(-q * T)
    disc_r = math.exp(-r * T)

    if option_type == "call":
        price = S * disc_q * Nd1 - K * disc_r * Nd2
        delta = disc_q * Nd1
        theta = (-S * disc_q * nd1 * sigma / (2 * math.sqrt(T))
                 - r * K * disc_r * Nd2
                 + q * S * disc_q * Nd1)
        rho = K * T * disc_r * Nd2
    else:
        price = K * disc_r * Nmd2 - S * disc_q * Nmd1
        delta = disc_q * (Nd1 - 1)
        theta = (-S * disc_q * nd1 * sigma / (2 * math.sqrt(T))
                 + r * K * disc_r * Nmd2
                 - q * S * disc_q * Nmd1)
        rho = -K * T * disc_r * Nmd2

    gamma = disc_q * nd1 / (S * sigma * math.sqrt(T))
    vega = S * disc_q * nd1 * math.sqrt(T)

    return {"price": price, "delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


def _fetch_futures_last(futures_symbol: str) -> Optional[float]:
    try:
        t = yf.Ticker(futures_symbol)
        hist = t.history(period="5d", interval="1d")
        if hist is not None and not hist.empty and not hist["Close"].dropna().empty:
            return float(hist["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return FALLBACK_SPOTS.get(futures_symbol)


def build_futures_greeks(
    tickers: List[str],
    moneyness_steps: List[float] = [-0.05, 0.0, 0.05],
    option_types: List[str] = ["call", "put"],
    r: float = DEFAULT_R,
    q: float = DEFAULT_Q,
    T: float = DEFAULT_T,
    sigma: float = DEFAULT_SIGMA,
) -> List[Dict]:
    rows: List[Dict] = []
    for tk in tickers:
        f_sym = FUTURES_PROXY.get(tk, "ES=F")
        S = _fetch_futures_last(f_sym)
        if S is None:
            continue

        for m in moneyness_steps:
            K = S * (1.0 + m)
            for ot in option_types:
                g = _bs_greeks(S=S, K=K, T=T, r=r, q=q, sigma=sigma, option_type=ot)
                row = GreeksRow(
                    ticker=tk,
                    futures_symbol=f_sym,
                    spot_proxy=S,
                    strike=K,
                    t_years=T,
                    r=r,
                    q=q,
                    sigma=sigma,
                    option_type=ot,
                    price=g["price"],
                    delta=g["delta"],
                    gamma=g["gamma"],
                    theta=g["theta"],
                    vega=g["vega"],
                    rho=g["rho"],
                )
                rows.append(asdict(row))
    return rows
