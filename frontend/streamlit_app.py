import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="S&P 500 Signals", layout="wide")
st.title("S&P 500 Signals Dashboard")

API_BASE = os.getenv("API_BASE_URL", "http://backend:8000")
st.caption(f"API: {API_BASE}")

@st.cache_data(ttl=30)
def fetch_signals():
    r = requests.get(f"{API_BASE}/signals", timeout=10)
    r.raise_for_status()
    return r.json()

try:
    payload = fetch_signals()
    signals = payload.get("signals", [])
    generated_at = payload.get("generated_at")

    if not signals:
        st.warning("No signals returned.")
        st.stop()

    df = pd.DataFrame(signals)

    c1, c2, c3 = st.columns(3)
    c1.metric("Signals", len(df))
    c2.metric("Buy", int((df["action"] == "BUY").sum()))
    c3.metric("Sell", int((df["action"] == "SELL").sum()))

    st.subheader("Signal Table")
    st.dataframe(df, use_container_width=True)

    st.subheader("Signal Scores")
    fig = px.bar(
        df.sort_values("score", ascending=False),
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
