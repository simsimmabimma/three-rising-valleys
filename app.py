import streamlit as st
import pandas as pd
import yfinance as yf
import random

st.set_page_config(layout="wide")
st.title("Three Rising Valleys Scanner")

# ----------------------------- Load tickers from your GitHub CSV -----------------------------
@st.cache_data
def load_custom_tickers():
    url = "https://raw.githubusercontent.com/simsimmabimma/three-rising-valleys/refs/heads/main/nasdaqlisted%20-%20Sheet1.csv"
    df = pd.read_csv(url)
    tickers = df.iloc[:, 0].dropna().unique().tolist()
    return tickers

# ----------------------------- Check for retracement pattern -----------------------------
def check_retracement(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        required_cols = ["Low", "High"]
        if not all(col in df.columns for col in required_cols):
            return None
        df = df.dropna(subset=required_cols)
        df["HL"] = df["Low"].rolling(window=3).min()
        df["HH"] = df["High"].rolling(window=3).max()
        valleys = df["HL"].dropna().values[-5:]
        peaks = df["HH"].dropna().values[-5:]

        if len(valleys) >= 3 and len(peaks) >= 2:
            if valleys[-1] > valleys[-2] > valleys[-3] and peaks[-1] > peaks[-2]:
                return {
                    "Ticker": ticker,
                    "Last Low": valleys[-1],
                    "Last High": peaks[-1]
                }
    except Exception as e:
        st.warning(f"Error checking {ticker}: {e}")
    return None

# ----------------------------- Scan a random batch of tickers -----------------------------
def scan_batch(tickers, batch_size=50):
    batch = random.sample(tickers, min(batch_size, len(tickers)))
    results = []
    for ticker in batch:
        res = check_retracement(ticker)
        if res:
            results.append(res)
    return results

# ----------------------------- Main app -----------------------------
def main():
    tickers = load_custom_tickers()
    st.write(f"✅ Loaded {len(tickers)} tickers from GitHub")

    if st.button("🔍 Scan for Three Rising Valleys"):
        with st.spinner("Scanning 50 random tickers..."):
            results = scan_batch(tickers, batch_size=50)
        if results:
            st.success(f"🎯 Found {len(results)} matching tickers!")
            st.dataframe(pd.DataFrame(results))
        else:
            st.info("No matching patterns found in this batch.")

if __name__ == "__main__":
    main()
