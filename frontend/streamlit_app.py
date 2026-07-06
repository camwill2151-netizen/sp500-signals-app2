import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="S&P 500 Signals", layout="wide")
st.title("S&P 500 Signals Dashboard")

API_BASE = os.getenv("API_BASE_URL", "http://backend:8000")
st.caption(f"API: {API_BASE}")

with st.sidebar:
    st.header("Controls")
    tickers = st.text_input("Tickers (comma-separated)", "AAPL,MSFT,NVDA,AMZN,GOOGL")
    period = st.selectbox("History period", ["1mo", "3mo", "6mo", "1y"], index=1)
    refresh = st.button("Refresh now")

@st.cache_data(ttl=60)
def fetch_signals(tickers_value: str, period_value: str):
    params = {"tickers": tickers_value, "period": period_value}
    r = requests.get(f"{API_BASE}/signals", params=params, timeout=20)
    r.raise_for_status()
    return r.json()

try:
    if refresh:
        fetch_signals.clear()

    payload = fetch_signals(tickers, period)
    signals = payload.get("signals", [])
    generated_at = payload.get("generated_at")

    if not signals:
        st.warning("No signals returned.")
        st.stop()

    df = pd.DataFrame(signals)
    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    c1, c2, c3 = st.columns(3)
    c1.metric("Signals", len(df))
    c2.metric("Buy", int((df["action"] == "BUY").sum()))
    c3.metric("Sell", int((df["action"] == "SELL").sum()))

    errs = df[df.get("error").notna()] if "error" in df.columns else pd.DataFrame()
    if not errs.empty:
        st.warning(f"{len(errs)} symbols had data issues.")
        st.dataframe(errs[["symbol", "error"]], use_container_width=True)

    st.subheader("Signal Table")
    st.dataframe(df[["symbol", "action", "score", "price", "timestamp"]], use_container_width=True)

    st.subheader("Signal Scores")
    plot_df = df.dropna(subset=["score"]).sort_values("score", ascending=False)
    fig = px.bar(
        plot_df,
        x="symbol",
        y="score",
        color="action",
        text="score",
        title="Score by Symbol",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(yaxis_range=[0, 1])
    st.plotly_chart(fig, use_container_width=True)

    if generated_at:
        st.caption(f"Generated at: {generated_at}")

except requests.RequestException as e:
    st.error(f"Failed to reach backend: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
