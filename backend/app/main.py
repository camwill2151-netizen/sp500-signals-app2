from typing import Optional, List
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import StockSignal
from .pipeline import build_signals_df
from .futures_greeks import build_futures_greeks
from .option_signal_engine import generate_option_signals
from .backtest_engine import run_backtest_multi

app = FastAPI(title="S&P 500 Signals API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SIGNALS_DF = pd.DataFrame()

@app.on_event("startup")
def startup_event():
    global SIGNALS_DF
    SIGNALS_DF = build_signals_df()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/refresh")
def refresh():
    global SIGNALS_DF
    SIGNALS_DF = build_signals_df()
    return {"status": "refreshed", "rows": int(len(SIGNALS_DF))}

@app.get("/signals", response_model=List[StockSignal])
def get_signals(signal: Optional[str] = None, sector: Optional[str] = None, ticker: Optional[str] = None, top_n: Optional[int] = 10):
    global SIGNALS_DF
    df = SIGNALS_DF.copy()

    if ticker and "ticker" in df.columns:
        df = df[df["ticker"].astype(str).str.upper() == ticker.upper()]
    if signal and "signal" in df.columns:
        df = df[df["signal"].astype(str).str.upper() == signal.upper()]
    if sector and "sector" in df.columns:
        df = df[df["sector"].astype(str).str.lower() == sector.lower()]

    if "final_score" in df.columns:
        df = df.sort_values("final_score", ascending=False).reset_index(drop=True)
        df["rank"] = df.index + 1

    if ticker is None and top_n is not None and top_n > 0:
        df = df.head(int(top_n))

    return df.to_dict(orient="records")


@app.get("/futures-greeks")
def futures_greeks(
    tickers: str = "SPY,QQQ,IWM,DIA",
    r: float = 0.05,
    q: float = 0.00,
    t_days: int = 30,
    sigma: float = 0.20,
):
    ticker_list = [x.strip().upper() for x in tickers.split(",") if x.strip()]
    T = max(t_days, 1) / 365.0
    data = build_futures_greeks(
        tickers=ticker_list,
        r=r,
        q=q,
        T=T,
        sigma=sigma,
    )
    return {"count": len(data), "rows": data}


@app.get("/option-signals")
def option_signals(
    tickers: str = "SPY,QQQ,IWM,DIA",
    r: float = 0.05,
    q: float = 0.00,
    t_days: int = 30,
    sigma: float = 0.20,
):
    ticker_list = [x.strip().upper() for x in tickers.split(",") if x.strip()]
    rows = generate_option_signals(
        tickers=ticker_list,
        r=r,
        q=q,
        t_days=t_days,
        sigma=sigma,
    )
    return {"count": len(rows), "rows": rows}


@app.get("/backtest-signals")
def backtest_signals(
    tickers: str = "SPY,QQQ,IWM,DIA",
    start_capital: float = 1000.0,
    option_type: str = "call",
):
    ticker_list = [x.strip().upper() for x in tickers.split(",") if x.strip()]
    return run_backtest_multi(
        tickers=ticker_list,
        start_capital=start_capital,
        option_type=option_type
    )
