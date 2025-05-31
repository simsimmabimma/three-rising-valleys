import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import math
from datetime import datetime

st.title("📉 Monthly 0.618 Retracement Scanner (NASDAQ)")

NASDAQ_URL = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"

@st.cache_data(ttl=86400)
def load_nasdaq_tickers():
    df = pd.read_csv(NASDAQ_URL)
    # The CSV has a column 'Symbol'
    tickers = df['Symbol'].tolist()
    return tickers

def log_fib_0618(low, high):
    # Log scale fib retracement
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    retracement_log = log_high - 0.618 * log_diff
    return round(math.exp(retracement_log), 2)

def check_retracement(ticker):
    try:
        # Download 4 years of monthly data, adjusted prices
        df = yf.download(ticker, period="4y", interval="1mo", progress=False, auto_adjust=True)
    except Exception:
        return None

    required_cols = ['Low', 'High', 'Close']
    if df.empty or not all(col in df.columns for col in required_cols):
        return None

    df = df.dropna(subset=required_cols)

    if len(df) < 36:  # require at least 3 years monthly data
        return None

    df = df.reset_index()

    # Take last 36 months (~3 years)
    recent = df.tail(36)

    # Find swing low (lowest low in recent 3 years)
    swing_low_row = recent.loc[recent['Low'].idxmin()]
    swing_low = swing_low_row['Low']
    swing_low_date = swing_low_row['Date']

    # Find swing high AFTER the swing low date
    after_low = recent[recent['Date'] > swing_low_date]
    if after_low.empty:
        return None
    swing_high_row = after_low.loc[after_low['High'].idxmax()]
    swing_high = swing_high_row['High']
    swing_high_date = swing_high_row['Date']

    # If swing high before swing low, no valid pattern
    if swing_high_date <= swing_low_date:
        return None

    # Calculate 0.618 fib retracement level in log scale
    retracement_price = log_fib_0618(swing_low, swing_high)

    # Check if stock price dipped to or below retracement in last 3 months
    last_3_months = recent.tail(3)
    dipped_below = (last_3_months['Low'] <= retracement_price).any()

    if dipped_below:
        return {
            "ticker": ticker,
            "swing_low": round(swing_low, 2),
            "swing_low_date": swing_low_date.strftime("%b %Y"),
            "swing_high": round(swing_high, 2),
            "swing_high_date": swing_high_date.strftime("%b %Y"),
            "retracement_0618": retracement_price,
            "last_low": round(last_3_months['Low'].min(), 2),
            "last_low_date": last_3_months.loc[last_3_months['Low'].idxmin(), 'Date'].strftime("%b %Y")
        }
    return None

def scan_batch(tickers, batch_size=50):
    results = []
    total = len(tickers)
    for i in range(0, total, batch_size):
        batch = tickers[i:i+batch_size]
        st.write(f"Scanning tickers {i+1} to {i+len(batch)} of {total}...")
        for ticker in batch:
            res = check_retracement(ticker)
            if res:
                results.append(res)
    return results

def main():
    st.write("Loading NASDAQ tickers...")
    tickers = load_nasdaq_tickers()
    st.write(f"Total tickers loaded: {len(tickers)}")

    if st.button("Start Scan"):
        with st.spinner("Scanning tickers for retracement dip... This will take some time."):
            results = scan_batch(tickers, batch_size=50)
        if results:
            st.success(f"Found {len(results)} tickers with retracement dip:")
            df_results = pd.DataFrame(results)
            st.dataframe(df_results)
        else:
            st.info("No tickers found with the retracement dip criteria.")

if __name__ == "__main__":
    main()
