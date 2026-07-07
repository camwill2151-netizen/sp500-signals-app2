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

    st.divider()
    st.header("Options Greeks")
    opt_ticker = st.text_input("Options ticker", "AAPL")
    expiry_index = st.number_input("Expiry index (0 = nearest)", min_value=0, value=0, step=1)
    num_strikes = st.slider("Strikes near ATM", 2, 10, 5)
    load_options_btn = st.button("Load Options")


@st.cache_data(ttl=60)
def fetch_signals(tickers_value: str, period_value: str):
    r = requests.get(f"{API_BASE}/signals", params={"tickers": tickers_value, "period": period_value}, timeout=20)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=60)
def fetch_options(ticker: str, expiry_index: int, num_strikes: int):
    r = requests.get(f"{API_BASE}/options", params={"ticker": ticker, "expiry_index": expiry_index, "num_strikes": num_strikes}, timeout=30)
    r.raise_for_status()
    return r.json()


st.header("📈 Price Signals")
try:
    if refresh:
        fetch_signals.clear()

    payload = fetch_signals(tickers, period)
    signals_data = payload.get("signals", [])
    generated_at = payload.get("generated_at")

    if not signals_data:
        st.warning("No signals returned.")
        st.stop()

    df = pd.DataFrame(signals_data)
    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    c1, c2, c3 = st.columns(3)
    c1.metric("Signals", len(df))
    c2.metric("Buy", int((df["action"] == "BUY").sum()))
    c3.metric("Sell", int((df["action"] == "SELL").sum()))

    if "error" in df.columns:
        errs = df[df["error"].notna()]
        if not errs.empty:
            st.warning(f"{len(errs)} symbols had data issues.")
            st.dataframe(errs[["symbol", "error"]], use_container_width=True)

    st.subheader("Signal Table")
    st.dataframe(df[["symbol", "action", "score", "price", "timestamp"]], use_container_width=True)

    st.subheader("Signal Scores")
    plot_df = df.dropna(subset=["score"]).sort_values("score", ascending=False)
    fig = px.bar(plot_df, x="symbol", y="score", color="action", text="score", title="Score by Symbol")
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(yaxis_range=[0, 1])
    st.plotly_chart(fig, use_container_width=True)

    if generated_at:
        st.caption(f"Generated at: {generated_at}")

except requests.RequestException as e:
    st.error(f"Failed to reach backend: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")


st.divider()
st.header("🔢 Options Greeks")

if load_options_btn:
    fetch_options.clear()

if load_options_btn or st.session_state.get("options_loaded"):
    st.session_state["options_loaded"] = True
    try:
        opt_data = fetch_options(opt_ticker, int(expiry_index), int(num_strikes))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ticker", opt_data["ticker"])
        col2.metric("Spot", f"${opt_data['spot']:.2f}")
        col3.metric("Expiry", opt_data["expiry"])
        col4.metric("Risk-Free Rate", f"{opt_data['risk_free_rate'] * 100:.2f}%")

        GREEK_COLS = ["contract", "strike", "last", "bid", "ask", "impliedVolatility", "volume", "openInterest", "delta", "gamma", "theta", "vega", "rho"]

        st.subheader("📗 Calls")
        calls_df = pd.DataFrame(opt_data["calls"])
        if not calls_df.empty:
            st.dataframe(calls_df[[c for c in GREEK_COLS if c in calls_df.columns]], use_container_width=True)

        st.subheader("📕 Puts")
        puts_df = pd.DataFrame(opt_data["puts"])
        if not puts_df.empty:
            st.dataframe(puts_df[[c for c in GREEK_COLS if c in puts_df.columns]], use_container_width=True)

        if not calls_df.empty and "delta" in calls_df.columns:
            st.subheader("Delta by Strike")
            chart_df = pd.concat([
                calls_df[["strike", "delta"]].assign(type="call"),
                puts_df[["strike", "delta"]].assign(type="put"),
            ]).dropna(subset=["delta"])
            fig2 = px.line(chart_df, x="strike", y="delta", color="type", markers=True, title=f"{opt_data['ticker']} Delta — {opt_data['expiry']}")
            st.plotly_chart(fig2, use_container_width=True)

        st.caption(f"Generated at: {opt_data['generated_at']}")

    except requests.RequestException as e:
        st.error(f"Failed to fetch options: {e}")
    except Exception as e:
        st.error(f"Unexpected error loading options: {e}")
else:
    st.info("Select a ticker in the sidebar and click **Load Options**.")

