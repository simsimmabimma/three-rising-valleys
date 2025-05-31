import streamlit as st
import pandas as pd
import yfinance as yf
import math
import random

st.set_page_config(page_title="Monthly 0.618 Retracement Scanner (Log Scale)")

NASDAQ_URL = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"

@st.cache_data(ttl=24*3600)
def load_all_nasdaq_tickers():
    df = pd.read_csv(NASDAQ_URL)
    tickers = df['Symbol'].str.upper().tolist()
    return tickers

def log_fib_0618(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    log_retracement = log_high - 0.618 * log_diff
    return math.exp(log_retracement)

def check_retracement(ticker):
    try:
        df = yf.download(ticker, period="4y", interval="1mo", progress=False, auto_adjust=True)
    except Exception:
        return None

    # Check if df is empty or does not have required columns
    if df.empty or 'Low' not in df.columns or 'High' not in df.columns:
        return None

    if df.shape[0] < 36:  # at least 3 years monthly data
        return None

    df = df.dropna(subset=['Low', 'High'])
    df = df.reset_index()

    # rest of your code ...


    recent = df.tail(12)

    # Find local low in recent 12 months
    local_low_idx = recent['Low'].idxmin()
    local_low = recent.loc[local_low_idx]

    # Find local high after low
    after_low = recent[recent.index > local_low_idx]
    if after_low.empty:
        return None
    local_high_idx = after_low['High'].idxmax()
    local_high = after_low.loc[local_high_idx]

    if local_high_idx <= local_low_idx:
        return None  # invalid pattern

    retrace_price = log_fib_0618(local_low['Low'], local_high['High'])

    # Check if price dipped to or below retrace_price in last 3 months after high
    after_high = recent[recent.index > local_high_idx]
    if after_high.empty:
        return None

    dip_found = False
    dip_date = None
    dip_price = None
    for _, row in after_high.iterrows():
        if row['Low'] <= retrace_price:
            dip_found = True
            dip_date = row['Date']
            dip_price = row['Low']
            break

    if dip_found:
        return {
            "Ticker": ticker,
            "Local Low": round(local_low['Low'], 2),
            "Local Low Date": local_low['Date'].strftime('%Y-%m'),
            "Local High": round(local_high['High'], 2),
            "Local High Date": local_high['Date'].strftime('%Y-%m'),
            "Retracement Price (0.618)": round(retrace_price, 2),
            "Dip Date": dip_date.strftime('%Y-%m'),
            "Dip Price": round(dip_price, 2),
        }

    return None

st.title("📉 Monthly 0.618 Retracement Scanner (Log Scale) - Nasdaq Tickers")

tickers = load_all_nasdaq_tickers()
st.write(f"Loaded {len(tickers)} Nasdaq tickers.")

if 'scanned_tickers' not in st.session_state:
    st.session_state.scanned_tickers = set()

if 'results' not in st.session_state:
    st.session_state.results = []

batch_size = st.number_input("Number of tickers to scan per batch", min_value=10, max_value=100, value=50)

def scan_batch():
    remaining = list(set(tickers) - st.session_state.scanned_tickers)
    if not remaining:
        st.warning("All tickers scanned.")
        return

    batch = random.sample(remaining, min(batch_size, len(remaining)))
    new_results = []
    progress_bar = st.progress(0)
    for i, ticker in enumerate(batch):
        st.write(f"Scanning {ticker}...")
        result = check_retracement(ticker)
        if result:
            new_results.append(result)
        st.session_state.scanned_tickers.add(ticker)
        progress_bar.progress((i+1)/len(batch))
    st.session_state.results.extend(new_results)
    progress_bar.empty()

if st.button("Scan Next Batch"):
    scan_batch()

if st.session_state.results:
    df_results = pd.DataFrame(st.session_state.results)
    st.write(f"Found {len(df_results)} tickers matching retracement criteria:")
    st.dataframe(df_results)
else:
    st.write("No matching tickers found yet.")

if st.button("Reset Scan"):
    st.session_state.scanned_tickers = set()
    st.session_state.results = []
    st.experimental_rerun()
