import streamlit as st
import yfinance as yf
import pandas as pd
import time

# URL to your CSV ticker list on GitHub (first column tickers)
TICKERS_URL = "https://raw.githubusercontent.com/simsimmabimma/three-rising-valleys/refs/heads/main/nasdaqlisted%20-%20Sheet1.csv"

@st.cache_data(ttl=24*3600)
def load_tickers():
    df = pd.read_csv(TICKERS_URL)
    tickers = df.iloc[:,0].dropna().astype(str).tolist()
    return tickers

def check_two_swing_higher_lows(df):
    """
    Check if df (monthly data sorted oldest to newest) has at least
    two swing higher lows with retracement >= 38% Fibonacci from previous low-high.
    """
    if len(df) < 6:
        return False, "Not enough data"

    lows = df['Low'].values
    highs = df['High'].values
    n = len(df)

    swings = []  # will hold (low, high) pairs of swings

    i = 0
    while i < n - 1:
        # Find low point
        low = lows[i]
        # Find next high after this low
        high_idx = None
        for j in range(i + 1, n):
            if highs[j] > highs[j-1]:
                high_idx = j
            else:
                break
        if high_idx is None:
            break
        high = highs[high_idx]

        # Save swing
        swings.append((low, high))

        # Find next retracement low after high
        retrace_idx = None
        for k in range(high_idx + 1, n):
            if lows[k] < lows[k-1]:
                retrace_idx = k
                break
        if retrace_idx is None:
            break

        retr_low = lows[retrace_idx]

        # Calculate retracement level
        prev_low, prev_high = low, high
        retracement_ratio = (prev_high - retr_low) / (prev_high - prev_low)

        if retracement_ratio < 0.38:
            # Not a deep enough retracement; skip forward
            i = retrace_idx + 1
            continue

        # Find next high after retracement low
        next_high_idx = None
        for m in range(retrace_idx + 1, n):
            if highs[m] > highs[m-1]:
                next_high_idx = m
            else:
                break
        if next_high_idx is None:
            break

        next_high = highs[next_high_idx]
        swings.append((retr_low, next_high))

        # If at least two swings found (two pairs), return True
        if len(swings) >= 4:
            return True, f"Found {len(swings)//2} swing higher lows with retracement >= 38%"

        i = next_high_idx + 1

    return False, "Pattern not found"

def scan_batch(tickers, batch_size=50):
    results = []
    for idx, ticker in enumerate(tickers):
        if idx % batch_size == 0 and idx != 0:
            st.write(f"Scanned {idx} tickers, pausing 10 seconds to avoid throttling...")
            time.sleep(10)

        st.write(f"Checking {ticker}...")
        try:
            data = yf.Ticker(ticker).history(period="5y", interval="1mo")
            if data.empty:
                st.write(f"No monthly data for {ticker}")
                continue

            # Sort by date ascending (oldest to newest)
            df = data.sort_index()

            found, msg = check_two_swing_higher_lows(df)
            if found:
                results.append((ticker, msg))
                st.write(f"**{ticker}** matches pattern: {msg}")
            else:
                st.write(f"{ticker}: {msg}")

        except Exception as e:
            st.write(f"Error checking {ticker}: {e}")

    return results

def main():
    st.title("Swing Higher Lows Pattern Scanner (Monthly Chart)")

    tickers = load_tickers()
    st.write(f"Loaded {len(tickers)} tickers.")

    batch_size = st.slider("Batch size (tickers per batch)", 10, 100, 50)

    if st.button("Run Scan"):
        results = scan_batch(tickers, batch_size)
        st.write("Scan complete.")
        st.write(f"Found {len(results)} tickers matching pattern:")
        for t, m in results:
            st.write(f"- {t}: {m}")

if __name__ == "__main__":
    main()
