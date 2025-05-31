import streamlit as st
import pandas as pd
import yfinance as yf
import time
import random

# Constants
CSV_URL = "https://raw.githubusercontent.com/simsimmabimma/three-rising-valleys/refs/heads/main/nasdaqlisted%20-%20Sheet1.csv"
BATCH_DELAY_SEC = 1

# Cache ticker loading
@st.cache_data
def load_tickers():
    df = pd.read_csv(CSV_URL)
    return df.iloc[:, 0].dropna().unique().tolist()

# Check retracement pattern
def check_retracement(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        required_cols = ['Low', 'High']
        if not all(col in df.columns for col in required_cols):
            return None

        df = df.dropna(subset=required_cols)
        if len(df) < 30:
            return None

        recent_lows = df['Low'].tail(30).values
        recent_highs = df['High'].tail(30).values

        low_valleys = sorted(recent_lows[-15:])[:3]
        if not (low_valleys[0] < low_valleys[1] < low_valleys[2]):
            return None

        retracement = (recent_highs[-1] - recent_lows[-1]) / recent_lows[-1]
        if retracement < 0.05:
            return None

        return ticker
    except Exception as e:
        st.warning(f"Error checking {ticker}: {e}")
        return None

# Scan tickers in batches
def scan_tickers(tickers, batch_size):
    if "scanned" not in st.session_state:
        st.session_state.scanned = set()
    if "results" not in st.session_state:
        st.session_state.results = []

    total = len(tickers)
    to_scan = [t for t in tickers if t not in st.session_state.scanned]
    random.shuffle(to_scan)

    progress = st.progress(0)
    scanned_count = 0

    for i in range(0, len(to_scan), batch_size):
        batch = to_scan[i:i + batch_size]
        for ticker in batch:
            result = check_retracement(ticker)
            st.session_state.scanned.add(ticker)
            if result:
                st.session_state.results.append(result)
        scanned_count += len(batch)
        progress.progress(min(scanned_count / total, 1.0))
        time.sleep(BATCH_DELAY_SEC)

    return st.session_state.results

# Main app
def main():
    st.title("Three Rising Valleys Scanner")
    tickers = load_tickers()

    st.sidebar.header("Settings")
    batch_size = st.sidebar.slider("Batch size", min_value=10, max_value=200, value=100, step=10)

    if st.sidebar.button("Start Scan"):
        with st.spinner("Scanning tickers..."):
            results = scan_tickers(tickers, batch_size)
        st.success(f"Scan complete. {len(results)} matches found.")
        st.write(results)

    if st.sidebar.button("Reset"):
        st.session_state.scanned = set()
        st.session_state.results = []
        st.success("Scan history cleared.")

    if "results" in st.session_state and st.session_state.results:
        st.subheader("Matched Tickers")
        st.write(st.session_state.results)

if __name__ == "__main__":
    main()
