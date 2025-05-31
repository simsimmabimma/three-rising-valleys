import yfinance as yf
import pandas as pd
import time
import random
import streamlit as st

# --- CONFIG ---
CSV_URL = "https://raw.githubusercontent.com/simsimmabimma/three-rising-valleys/refs/heads/main/nasdaqlisted%20-%20Sheet1.csv"
BATCH_SIZE = 50
SLEEP_BETWEEN_CALLS = 0.5  # seconds

# --- LOAD TICKERS ---
@st.cache_data
def load_tickers():
    df = pd.read_csv(CSV_URL)
    tickers = df.iloc[:, 0].dropna().unique().tolist()
    return tickers

# --- CHECK FOR PATTERN ---
def check_retracement(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, threads=False)

        if df.empty or not all(col in df.columns for col in ["Low", "High"]):
            print(f"Missing data for {ticker}")
            return None

        df = df.dropna(subset=["Low", "High"])
        if df.empty:
            print(f"Empty after dropping NaNs: {ticker}")
            return None

        df["HL"] = df["Low"].rolling(window=3).min()
        df["HH"] = df["High"].rolling(window=3).max()

        valleys = df["HL"].dropna().values[-5:]
        peaks = df["HH"].dropna().values[-5:]

        if len(valleys) >= 3 and len(peaks) >= 2:
            if valleys[-1] > valleys[-2] > valleys[-3] and peaks[-1] > peaks[-2]:
                return {
                    "Ticker": ticker,
                    "Last Low": round(valleys[-1], 2),
                    "Last High": round(peaks[-1], 2)
                }

    except Exception as e:
        print(f"Error checking {ticker}: {e}")
    return None

# --- PROCESS ALL TICKERS IN BATCHES ---
def scan_all_tickers(tickers, batch_size):
    st.write(f"Total tickers to scan: {len(tickers)}")
    results = []
    seen = set()
    remaining = set(tickers)

    while remaining:
        batch = random.sample(list(remaining), min(batch_size, len(remaining)))
        for ticker in batch:
            st.write(f"Scanning: {ticker}")
            result = check_retracement(ticker)
            if result:
                st.success(f"Pattern found: {result['Ticker']}")
                results.append(result)
            seen.add(ticker)
            remaining.remove(ticker)
            time.sleep(SLEEP_BETWEEN_CALLS)

        st.write(f"{len(seen)} tickers scanned so far, {len(remaining)} remaining...")

    return results

# --- MAIN ---
def main():
    st.title("📈 Three Rising Valleys Pattern Scanner")
    tickers = load_tickers()

    if st.button("Start Scan"):
        results = scan_all_tickers(tickers, BATCH_SIZE)
        st.success(f"✅ Scan complete. {len(results)} matches found.")

        if results:
            df_results = pd.DataFrame(results)
            st.dataframe(df_results)
            csv = df_results.to_csv(index=False).encode("utf-8")
            st.download_button("Download Results as CSV", csv, "pattern_results.csv", "text/csv")

if __name__ == "__main__":
    main()
