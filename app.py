import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

API_KEY = "YOUR_POLYGON_API_KEY"
BASE_URL = "https://api.polygon.io"

st.set_page_config(page_title="Fib .618 Retracement (Last 3 Months)", layout="wide")
st.title("🔍 Monthly .618 Fibonacci Retracement Scanner")

@st.cache_data(ttl=24*3600)
def get_nasdaq_tickers():
    url = f"{BASE_URL}/v3/reference/tickers?market=stocks&exchange=XNAS&active=true&limit=1000&apiKey={API_KEY}"
    tickers = []
    page = 1
    while True:
        resp = requests.get(url + f"&page={page}")
        if resp.status_code != 200:
            break
        data = resp.json()
        results = data.get("results", [])
        if not results:
            break
        tickers += [r["ticker"] for r in results]
        if not data.get("next_url"):
            break
        page += 1
        time.sleep(0.2)
        if len(tickers) >= 1000:
            break
    return tickers[:1000]

def get_monthly_agg(ticker):
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/month/2022-01-01/2025-12-31?adjusted=true&sort=desc&limit=60&apiKey={API_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return None
    df = pd.DataFrame(results)
    df['t'] = pd.to_datetime(df['t'], unit='ms')
    df.set_index('t', inplace=True)
    df.rename(columns={'l':'Low','h':'High','o':'Open','c':'Close','v':'Volume'}, inplace=True)
    return df.sort_index()

def check_618_retracement_last_3m(df):
    if df is None or len(df) < 3:
        return False

    recent = df.iloc[-3:]
    low_idx = recent['Close'].idxmin()
    high_idx = recent['Close'].idxmax()

    if low_idx == high_idx:
        return False  # not a clear range

    low_log = np.log(df.loc[low_idx, 'Close'])
    high_log = np.log(df.loc[high_idx, 'Close'])

    fib_618_log = low_log + 0.618 * (high_log - low_log)
    fib_618_price = np.exp(fib_618_log)

    tolerance = 0.03  # 3%
    return any(
        abs(price - fib_618_price) / fib_618_price <= tolerance
        for price in recent['Close']
    )

if "tickers" not in st.session_state:
    with st.spinner("Fetching tickers list from Polygon.io..."):
        st.session_state.tickers = get_nasdaq_tickers()

max_tickers = 100
st.write(f"Scanning first **{max_tickers}** NASDAQ stocks...")

if st.button("Run Scan"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(st.session_state.tickers[:max_tickers]):
        status_text.text(f"Scanning {ticker} ({i+1}/{max_tickers})")
        df = get_monthly_agg(ticker)
        if check_618_retracement_last_3m(df):
            results.append(ticker)
        progress_bar.progress((i + 1) / max_tickers)
        time.sleep(0.2)

    status_text.text(f"Done! Found {len(results)} matches.")
    if results:
        st.success("✅ Matching tickers:")
        st.write(results)
    else:
        st.warning("❌ No tickers matched the 0.618 retracement in the last 3 months.")


