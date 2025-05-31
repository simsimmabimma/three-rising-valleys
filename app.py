import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random

# URL to your raw CSV with tickers
TICKERS_CSV_URL = "https://raw.githubusercontent.com/simsimmabimma/three-rising-valleys/refs/heads/main/nasdaqlisted%20-%20Sheet1.csv"

@st.cache_data
def load_tickers():
    df = pd.read_csv(TICKERS_CSV_URL)
    # Assumes first column is tickers, drop NA and duplicates
    tickers = df.iloc[:, 0].dropna().unique().tolist()
    return tickers

def check_retracement(ticker):
    """Check retracement pattern for one ticker.
    Returns (ticker, True/False, reason or None)"""
    try:
        df = yf.download(ticker, period="2y", interval="1mo", progress=False)
        if df.empty:
            return ticker, False, "No data"
        required_cols = ['Low', 'High']
        if not all(col in df.columns for col in required_cols):
            return ticker, False, "Missing required columns"
        df = df.dropna(subset=required_cols)
        if len(df) < 6:
            return ticker, False, "Not enough monthly data"
        # Your retracement logic here:
        # Example simplified:
        highs = df['High']
        lows = df['Low']
        max_high = highs.max()
        min_low = lows.min()
        retracement = (max_high - min_low) / max_high
        # Just example: retracement > 0.15 means True
        if retracement > 0.15:
            return ticker, True, None
        else:
            return ticker, False, "No significant retracement"
    except Exception as e:
        return ticker, False, f"Error: {str(e)}"

def scan_batch(tickers, batch_size, scanned):
    batch = []
    for t in tickers:
        if t not in scanned:
            batch.append(t)
        if len(batch) == batch_size:
            break
    results = []
    for ticker in batch:
        res = check_retracement(ticker)
        results.append(res)
        scanned.add(ticker)
        time.sleep(0.5)  # simple throttling delay, adjust as needed
    return results

def main():
    st.title("3 Rising Valleys Scanner")

    tickers = load_tickers()

    # Initialize scanned tickers set in session state
    if "scanned" not in st.session_state:
        st.session_state.scanned = set()

    st.sidebar.header("Settings")
    batch_size = st.sidebar.slider("Batch size", min_value=10, max_value=200, value=100, step=10)

    if st.sidebar.button("Reset Scan"):
        st.session_state.scanned.clear()
        st.success("Scan reset! Ready to start fresh.")

    if st.sidebar.button("Start Scan") or st.session_state.get("auto_scan", False):
        st.session_state.auto_scan = True
        remaining = [t for t in tickers if t not in st.session_state.scanned]
        if not remaining:
            st.success("All tickers scanned!")
            st.session_state.auto_scan = False
        else:
            with st.spinner(f"Scanning batch of up to {batch_size} tickers..."):
                results = scan_batch(remaining, batch_size, st.session_state.scanned)
            # Show results incrementally
            for ticker, passed, reason in results:
                if passed:
                    st.success(f"{ticker}: Pattern detected!")
                else:
                    st.info(f"{ticker}: {reason}")

            # Auto-run next batch if there are more
            if len(st.session_state.scanned) < len(tickers):
                st.experimental_rerun()
            else:
                st.success("Scanning complete for all tickers.")
                st.session_state.auto_scan = False

    else:
        st.write(f"Ready to scan {len(tickers)} tickers.")
        scanned_count = len(st.session_state.scanned)
        st.write(f"Tickers scanned so far: {scanned_count}")

if __name__ == "__main__":
    main()
