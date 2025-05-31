import streamlit as st
import yfinance as yf
import pandas as pd
import math
from datetime import datetime
import random

st.title("📉 Monthly 0.618 Retracement Scanner")

@st.cache_data(ttl=3600)
def load_nasdaq_tickers():
    url = "https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")
    # Remove rows with test issue or empty symbols
    tickers = df['Symbol'].tolist()
    tickers = [t for t in tickers if t and t != 'Symbol']
    return tickers

def log_fib_0618(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    log_retracement = log_high - 0.618 * log_diff
    return round(math.exp(log_retracement), 2)

def check_retracement(ticker):
    try:
        df = yf.download(ticker, period="4y", interval="1mo", progress=False, auto_adjust=True)
    except Exception:
        return None

    required_cols = ['Low', 'High', 'Close']

    if df.empty:
        return None

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return None

    df = df.dropna(subset=required_cols)

    if len(df) < 36:
        return None

    df = df.reset_index()

    # Use last 36 months (3 years)
    recent = df[-36:]

    # Find local low first, then local high after it
    local_low_row = recent.loc[recent['Low'].idxmin()]
    low_index = recent['Low'].idxmin()
    local_high_rows = recent.loc[recent.index > low_index]

    if local_high_rows.empty:
        return None

    local_high_row = local_high_rows.loc[local_high_rows['High'].idxmax()]
    high_index = local_high_rows['High'].idxmax()

    if high_index <= low_index:
        return None

    retrace_price = log_fib_0618(local_low_row['Low'], local_high_row['High'])

    latest = recent.iloc[-1]

    # Check if latest close dipped to or below the retracement level
    if latest['Close'] <= retrace_price:
        return {
            "ticker": ticker,
            "low": local_low_row['Low'],
            "high": local_high_row['High'],
            "retracement_level": retrace_price,
            "latest_close": latest['Close'],
            "latest_date": latest['Date'].strftime("%b %Y")
        }
    return None

def scan_batch(tickers, batch_size=50):
    results = []
    tickers_to_scan = random.sample(tickers, min(batch_size, len(tickers)))
    for ticker in tickers_to_scan:
        result = check_retracement(ticker)
        if result:
            results.append(result)
    return results

def main():
    tickers = load_nasdaq_tickers()
    st.write(f"Loaded {len(tickers)} NASDAQ tickers.")

    batch_size = st.number_input("Batch size per scan", min_value=10, max_value=100, value=50)

    if st.button("Scan Batch"):
        with st.spinner(f"Scanning {batch_size} random tickers for retracement..."):
            results = scan_batch(tickers, batch_size)
        if results:
            st.success(f"Found {len(results)} tickers that dipped to/below 0.618 retracement level.")
            for r in results:
                st.write(f"**{r['ticker']}** - Low: {r['low']}, High: {r['high']}, "
                         f"Retracement Level: {r['retracement_level']}, "
                         f"Latest Close ({r['latest_date']}): {r['latest_close']}")
        else:
            st.info("No tickers found in this batch with a dip to or below 0.618 retracement level.")

if __name__ == "__main__":
    main()
