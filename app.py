import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

API_KEY = "A_xj1Mwz42bTgVFi6Hz0gOEm4Olk9aDH"
BASE_URL = "https://api.polygon.io"

st.set_page_config(page_title="Fib Retracement Scanner (Polygon.io)", layout="wide")
st.title("📊 Monthly Fib Retracement Scanner using Polygon.io")

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
        time.sleep(0.2)  # be kind to API
        if len(tickers) >= 1000:
            break
    return tickers[:1000]  # limit for demo

def get_monthly_agg(ticker):
    # Get last 5 years monthly aggregates
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/month/2018-01-01/2023-12-31?adjusted=true&sort=asc&limit=120&apiKey={API_KEY}"
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
    return df

def fib_retracement_scan_polygon(df):
    if df is None or len(df) < 24:
        return False
    df['log_close'] = np.log(df['Close'])

    last_12m = df.iloc[-12:]
    low_idx = last_12m['Close'].idxmin()
    low_log_price = df.loc[low_idx, 'log_close']

    after_low = df.loc[low_idx:]
    peak_log_price = after_low['log_close'].max()

    fib_618_log = low_log_price + 0.618 * (peak_log_price - low_log_price)
    fib_618_price = np.exp(fib_618_log)

    last_3m = df.iloc[-3:]
    tolerance = 0.03  # 3%

    retraced = any(
        abs(price - fib_618_price) / fib_618_price <= tolerance
        for price in last_3m['Close']
    )

    return retraced

if "tickers" not in st.session_state:
    with st.spinner("Fetching tickers list from Polygon.io..."):
        st.session_state.tickers = get_nasdaq_tickers()

max_tickers = 100  # limit for demo
st.write(f"Scanning first **{max_tickers}** NASDAQ tickers from Polygon.io...")

if st.button("Run Scan"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(st.session_state.tickers[:max_tickers]):
        status_text.text(f"Scanning {ticker} ({i+1}/{max_tickers})")
        df = get_monthly_agg(ticker)
        if fib_retracement_scan_polygon(df):
            results.append(ticker)
        progress_bar.progress((i + 1) / max_tickers)
        time.sleep(0.1)  # avoid API rate limits

    status_text.text(f"Scan complete! Found {len(results)} matches.")
    if results:
        st.write("Tickers matching fib retracement scan:")
        st.write(results)
    else:
        st.write("No tickers matched the criteria.")

