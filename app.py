import streamlit as st
import pandas as pd
import yfinance as yf
import time

@st.cache_data
def load_nasdaq_tickers():
    url = "https://raw.githubusercontent.com/simsimmabimma/three-rising-valleys/refs/heads/main/nasdaqlisted%20-%20Sheet1.csv"
    df = pd.read_csv(url)
    tickers = df.iloc[:, 0].dropna().unique().tolist()
    return tickers

def check_batch_retracement(ticker_data: pd.DataFrame):
    results = []
    for ticker in ticker_data.columns.levels[0]:
        try:
            df = ticker_data[ticker].dropna(subset=["Low", "High"])

            if df.empty or len(df) < 10:
                continue

            df["HL"] = df["Low"].rolling(window=3).min()
            df["HH"] = df["High"].rolling(window=3).max()

            valleys = df["HL"].dropna().values[-5:]
            peaks = df["HH"].dropna().values[-5:]

            if len(valleys) >= 3 and len(peaks) >= 2:
                if valleys[-1] > valleys[-2] > valleys[-3] and peaks[-1] > peaks[-2]:
                    results.append({
                        "Ticker": ticker,
                        "Last Low": round(valleys[-1], 2),
                        "Last High": round(peaks[-1], 2)
                    })

        except Exception as e:
            st.warning(f"Error processing {ticker}: {e}")

    return results

def scan_all_tickers_vectorized(tickers, batch_size):
    st.write(f"Scanning {len(tickers)} tickers in batches of {batch_size}")
    results = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        st.write(f"Fetching batch {i // batch_size + 1}: {len(batch)} tickers")
        try:
            data = yf.download(batch, period="3mo", interval="1d", group_by="ticker", progress=False, threads=True)
            batch_results = check_batch_retracement(data)
            results.extend(batch_results)
        except Exception as e:
            st.error(f"Batch failed: {e}")
        time.sleep(1)  # Adjust based on throttling observed
    return results

def main():
    st.title("Three Rising Valleys Screener")
    tickers = load_nasdaq_tickers()
    batch_size = st.slider("Select batch size", min_value=50, max_value=500, step=50, value=200)

    if st.button("Start Scan"):
        results = scan_all_tickers_vectorized(tickers, batch_size)
        st.success(f"Scan complete. {len(results)} tickers found.")
        st.dataframe(pd.DataFrame(results))

if __name__ == "__main__":
    main()
