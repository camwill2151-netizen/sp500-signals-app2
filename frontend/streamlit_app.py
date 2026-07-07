
import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import plotly.graph_objects as go
import yfinance as yf
from math import log, sqrt, exp, erf, pi
from datetime import datetime, timezone
from bs4 import BeautifulSoup

API_BASE = "http://backend:8000"
COINGLASS_API_BASE = "https://open-api-v4.coinglass.com"
COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY", "")
st.set_page_config(page_title="S&P 500 Signals", layout="wide")
st.title("S&P 500 Signals Dashboard")

top_n = st.slider("Top N stocks", 5, 200, 25, 5)
signal = st.selectbox("Signal", ["ALL", "BUY", "HOLD", "SELL"])

params = {"top_n": int(top_n)}
if signal != "ALL":
    params["signal"] = signal

@st.cache_data(ttl=60)
def load_data(p):
    r = requests.get(f"{API_BASE}/signals", params=p, timeout=60)
    r.raise_for_status()
    return pd.DataFrame(r.json())

@st.cache_data(ttl=900)
def load_ohlc(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    t = ticker.replace(".", "-")
    hist = yf.Ticker(t).history(period=period, interval=interval, auto_adjust=False)
    if hist is None or hist.empty:
        return pd.DataFrame()
    hist = hist.reset_index()
    if "Date" in hist.columns:
        hist = hist.rename(columns={"Date": "dt"})
    elif "Datetime" in hist.columns:
        hist = hist.rename(columns={"Datetime": "dt"})
    keep = [c for c in ["dt", "Open", "High", "Low", "Close", "Volume"] if c in hist.columns]
    return hist[keep].dropna(subset=["Open", "High", "Low", "Close"]).copy()




@st.cache_data(ttl=600)
def load_optionstrategist_volatility(symbol: str) -> float:
    url = "https://www.optionstrategist.com/calculators/free-volatility-data"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        txt = soup.get_text("\n", strip=True)
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        sym = str(symbol).upper().replace(".", "")
        import re

        # strict token match first
        for ln in lines:
            toks = re.split(r"\s+", ln.upper())
            if sym in toks:
                nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+", ln)]
                cand = next((v for v in nums if 1.0 <= v <= 400.0), None)
                if cand is not None:
                    return cand / 100.0

        # fallback contains match
        for ln in lines:
            if sym in ln.upper():
                nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+", ln)]
                cand = next((v for v in nums if 1.0 <= v <= 400.0), None)
                if cand is not None:
                    return cand / 100.0

        return float("nan")
    except Exception:
        return float("nan")

@st.cache_data(ttl=900)
def compute_volatility(ohlc: pd.DataFrame) -> float:
    if ohlc is None or ohlc.empty or "Close" not in ohlc.columns:
        return float("nan")
    r = ohlc["Close"].pct_change().dropna()
    if r.empty:
        return float("nan")
    return float(r.std() * (252 ** 0.5))

def _norm_cdf(x):
    return 0.5*(1.0+erf(x/sqrt(2.0)))
def _norm_pdf(x):
    return (1.0/sqrt(2.0*pi))*exp(-0.5*x*x)
def _bs_greeks(S,K,T,r,sigma,is_call):
    if S<=0 or K<=0 or T<=0 or sigma<=0: return {"delta":float("nan"),"gamma":float("nan"),"theta":float("nan"),"vega":float("nan"),"rho":float("nan")}
    d1=(log(S/K)+(r+0.5*sigma*sigma)*T)/(sigma*sqrt(T)); d2=d1-sigma*sqrt(T)
    if is_call:
        delta=_norm_cdf(d1); theta=(-(S*_norm_pdf(d1)*sigma)/(2*sqrt(T)) - r*K*exp(-r*T)*_norm_cdf(d2))/365.0; rho=(K*T*exp(-r*T)*_norm_cdf(d2))/100.0
    else:
        delta=_norm_cdf(d1)-1.0; theta=(-(S*_norm_pdf(d1)*sigma)/(2*sqrt(T)) + r*K*exp(-r*T)*_norm_cdf(-d2))/365.0; rho=(-K*T*exp(-r*T)*_norm_cdf(-d2))/100.0
    gamma=_norm_pdf(d1)/(S*sigma*sqrt(T)); vega=(S*_norm_pdf(d1)*sqrt(T))/100.0
    return {"delta":float(delta),"gamma":float(gamma),"theta":float(theta),"vega":float(vega),"rho":float(rho)}
@st.cache_data(ttl=900)
def load_option_greeks(ticker, rf_rate=0.045):
    try:
        t=yf.Ticker(str(ticker).replace(".","-")); h=t.history(period="1mo", interval="1d", auto_adjust=False)
        if h is None or h.empty or "Close" not in h.columns: return None
        S=float(h["Close"].dropna().iloc[-1]); ex=t.options
        if not ex: return None
        e=ex[0]; ch=t.option_chain(e); calls=ch.calls.copy() if ch and ch.calls is not None else pd.DataFrame(); puts=ch.puts.copy() if ch and ch.puts is not None else pd.DataFrame()
        if calls.empty and puts.empty: return None
        c=[]
        if not calls.empty: calls["is_call"]=True; calls["dist"]=(calls["strike"]-S).abs(); c.append(calls)
        if not puts.empty: puts["is_call"]=False; puts["dist"]=(puts["strike"]-S).abs(); c.append(puts)
        z=pd.concat(c, ignore_index=True).sort_values("dist")
        row=None
        for _,r in z.iterrows():
            iv=r.get("impliedVolatility", float("nan")); k=r.get("strike", float("nan"))
            if pd.notna(iv) and iv and iv>0 and pd.notna(k) and k>0: row=r; break
        if row is None: return None
        K=float(row["strike"]); sigma=float(row["impliedVolatility"]); is_call=bool(row["is_call"])
        exp_dt=datetime.strptime(e, "%Y-%m-%d").replace(tzinfo=timezone.utc); now=datetime.now(timezone.utc); T=max((exp_dt-now).total_seconds(),0.0)/(365.0*24*3600.0); T=max(T,1e-6)
        return _bs_greeks(S,K,T,float(rf_rate),sigma,is_call)
    except Exception:
        return None

try:
    df = load_data(params)
except Exception as e:
    st.error(f"Backend unavailable: {e}")
    st.stop()

if df.empty:
    st.warning("No data returned.")
    st.stop()

if "final_score" in df.columns:
    df = df.sort_values("final_score", ascending=False).reset_index(drop=True)
if "rank" not in df.columns:
    df["rank"] = df.index + 1

def make_price_trend(row):
    base = float(row.get("sma_200", 100))
    mid = float(row.get("sma_50", base * 1.03))
    last = float(row.get("last_close", mid * 1.01))
    pts = np.interp(np.arange(12), [0, 6, 11], [base, mid, last])
    return [round(x, 2) for x in pts]

def make_score_trend(row):
    f = float(row.get("fundamental_score", 50))
    t = float(row.get("technical_score", 50))
    s = float(row.get("sentiment_score", 50))
    avg = float(row.get("final_score", (f + t + s) / 3))
    pts = np.interp(np.arange(12), [0, 4, 8, 11], [f, t, s, avg])
    return [round(x, 2) for x in pts]

df["price_trend"] = df.apply(make_price_trend, axis=1)
df["score_trend"] = df.apply(make_score_trend, axis=1)

def _trend_dir(vals):
    if not isinstance(vals, list) or len(vals) < 2:
        return "HOLD"
    return "BUY" if vals[-1] > vals[0] else ("SELL" if vals[-1] < vals[0] else "HOLD")

def _trend_arrow(d):
    return "🟢 ↑ BUY" if d=="BUY" else ("🔴 ↓ SELL" if d=="SELL" else "🟡 → HOLD")


base_cols = [c for c in [
    "rank", "ticker", "company", "sector", "signal", "final_score",
    "fundamental_score", "technical_score", "sentiment_score"
] if c in df.columns]
table_df = df[base_cols + ["price_trend", "score_trend"]].copy()
table_df["price_trend_signal"] = table_df["price_trend"].apply(_trend_dir)
table_df["score_trend_signal"] = table_df["score_trend"].apply(_trend_dir)
table_df["price_trend_dir"] = table_df["price_trend_signal"].apply(_trend_arrow)
table_df["score_trend_dir"] = table_df["score_trend_signal"].apply(_trend_arrow)

st.dataframe(
    table_df,
    width="stretch",
    height=620,
    column_config={
        "price_trend": st.column_config.LineChartColumn("Price Trend"),
        "score_trend": st.column_config.LineChartColumn("Score Trend", y_min=0, y_max=100),
        "price_trend_dir": st.column_config.TextColumn("Price Trend Signal"),
        "score_trend_dir": st.column_config.TextColumn("Score Trend Signal"),
        "greek_delta": st.column_config.NumberColumn("Δ Delta", format="%.4f"),
        "greek_gamma": st.column_config.NumberColumn("Γ Gamma", format="%.4f"),
        "greek_theta": st.column_config.NumberColumn("Θ Theta", format="%.4f"),
        "greek_vega": st.column_config.NumberColumn("Vega", format="%.4f"),
        "greek_rho": st.column_config.NumberColumn("Rho", format="%.4f"),
    },
)

st.divider()
st.subheader("Ticker Detail OHLC")

if "ticker" in df.columns and len(df) > 0:
    ticker_list = df["ticker"].dropna().astype(str).tolist()
    picked = st.selectbox("Select ticker", ticker_list, index=0)

    ohlc = load_ohlc(picked, period="6mo", interval="1d")
    if ohlc.empty:
        st.warning(f"No OHLC market data found for {picked}.")
    else:
        ohlc = ohlc.copy()
        ohlc["bar_signal"] = np.where(
            ohlc["Close"] > ohlc["Open"], "BUY",
            np.where(ohlc["Close"] < ohlc["Open"], "SELL", "HOLD")
        )
        color_map = {"BUY": "#16a34a", "HOLD": "#eab308", "SELL": "#dc2626"}
        ohlc["color"] = ohlc["bar_signal"].map(color_map).fillna("#6b7280")

        counts = ohlc["bar_signal"].value_counts().to_dict()
        st.caption("Candle mix - BUY: {} | HOLD: {} | SELL: {}".format(counts.get('BUY',0), counts.get('HOLD',0), counts.get('SELL',0)))

        fig = go.Figure()
        for _, rr in ohlc.iterrows():
            fig.add_shape(
                type="line",
                x0=rr["dt"], x1=rr["dt"],
                y0=rr["Low"], y1=rr["High"],
                line=dict(color=rr["color"], width=1)
            )
        fig.add_trace(go.Ohlc(
            x=ohlc["dt"],
            open=ohlc["Open"],
            high=ohlc["High"],
            low=ohlc["Low"],
            close=ohlc["Close"],
            increasing_line_color="rgba(0,0,0,0)",
            decreasing_line_color="rgba(0,0,0,0)",
            name=picked,
            hovertext=ohlc["bar_signal"],
            hoverinfo="x+y+text"
        ))
        fig.add_trace(go.Scatter(
            x=ohlc["dt"],
            y=ohlc["Close"],
            mode="markers",
            marker=dict(size=5, color=ohlc["color"]),
            name="Signal color",
            hovertext=ohlc["bar_signal"],
            hoverinfo="x+y+text"
        ))
        fig.update_layout(
            title=f"{picked} OHLC (per-candle signal colors)",
            height=560,
            xaxis_title="Date",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, width="stretch")

        # Volatility chart UNDER OHLC
        vol = load_optionstrategist_volatility(picked)
        if pd.isna(vol):
            vol = load_optionstrategist_volatility(picked)
        if pd.isna(vol):
            vol = compute_volatility(ohlc)
        vol_value = 0.0 if pd.isna(vol) else float(vol)

        fig_vol = go.Figure(go.Bar(
            x=["Volatility"],
            y=[vol_value],
            marker_color="#60a5fa",
            text=[f"{vol_value:.2%}"],
            textposition="outside"
        ))
        fig_vol.update_layout(
            title=f"{picked} Annualized Volatility",
            height=260,
            yaxis_title="Volatility",
            xaxis_title="",
            yaxis_tickformat=".0%",
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig_vol, width="stretch")

        # Greeks line graph
        g = load_option_greeks(picked) if "load_option_greeks" in globals() else None
        st.markdown("#### Options Greeks")
        if not g:
            st.info("No options greeks available for this ticker.")
        else:
            greek_names = ["Delta", "Gamma", "Theta", "Vega", "Rho"]
            greek_vals = [g.get("delta", float("nan")), g.get("gamma", float("nan")), g.get("theta", float("nan")), g.get("vega", float("nan")), g.get("rho", float("nan"))]
            fig_g = go.Figure()
            fig_g.add_trace(go.Scatter(x=greek_names, y=greek_vals, mode="lines+markers", name="Greeks", line=dict(width=3)))
            fig_g.update_layout(height=260, margin=dict(l=10,r=10,t=30,b=10), yaxis_title="Value", xaxis_title="Greek")
            st.plotly_chart(fig_g, width="stretch")
else:
    st.info("No ticker data available.")



st.subheader("Futures-Based Manual Greeks")

col1, col2, col3, col4 = st.columns(4)
r_in = col1.number_input("Risk-free rate (r)", min_value=0.0, max_value=0.30, value=0.05, step=0.005)
q_in = col2.number_input("Carry/Dividend yield (q)", min_value=0.0, max_value=0.30, value=0.00, step=0.005)
t_in = col3.number_input("Tenor (days)", min_value=1, max_value=365, value=30, step=1)
sig_in = col4.number_input("Volatility (sigma)", min_value=0.01, max_value=2.00, value=0.20, step=0.01)

tickers_csv = st.text_input("Tickers (comma-separated)", value="SPY,QQQ,IWM,DIA")

if st.button("Load Futures Greeks"):
    try:
        resp = requests.get(
            f"{API_BASE}/futures-greeks",
            params={"tickers": tickers_csv, "r": r_in, "q": q_in, "t_days": int(t_in), "sigma": sig_in},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("rows", [])
        if not rows:
            st.info("No futures greeks rows returned.")
        else:
            df_fg = pd.DataFrame(rows)
            st.dataframe(df_fg, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to load futures greeks: {e}")



st.subheader("Option Buy/Sell Signals (Tech + Fundamental + Greeks)")

sig_tickers = st.text_input("Signal tickers (comma-separated)", value="SPY,QQQ,IWM,DIA")
c1, c2, c3, c4 = st.columns(4)
sig_r = c1.number_input("Signal r", min_value=0.0, max_value=0.30, value=0.05, step=0.005, key="sig_r")
sig_q = c2.number_input("Signal q", min_value=0.0, max_value=0.30, value=0.00, step=0.005, key="sig_q")
sig_t = c3.number_input("Signal tenor (days)", min_value=1, max_value=365, value=30, step=1, key="sig_t")
sig_sigma = c4.number_input("Signal sigma", min_value=0.01, max_value=2.0, value=0.20, step=0.01, key="sig_sigma")

if st.button("Generate Option Signals"):
    try:
        r = requests.get(
            f"{API_BASE}/option-signals",
            params={
                "tickers": sig_tickers,
                "r": sig_r,
                "q": sig_q,
                "t_days": int(sig_t),
                "sigma": sig_sigma,
            },
            timeout=45,
        )
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("rows", [])
        if not rows:
            st.info("No signal rows returned.")
        else:
            df_sig = pd.DataFrame(rows)
            show_cols = [
                "ticker","futures_symbol","option_type","strike","price",
                "delta","gamma","theta","vega","rho",
                "tech_score","fund_score","rsi14","macd_hist","signal"
            ]
            show_cols = [c for c in show_cols if c in df_sig.columns]
            st.dataframe(df_sig[show_cols], use_container_width=True)
    except Exception as e:
        st.error(f"Signal generation failed: {e}")
