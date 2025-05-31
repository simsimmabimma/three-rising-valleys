import streamlit as st
import pandas as pd
import yfinance as yf
import time
import random

# CONFIG
CSV_URL = "https://raw.githubusercontent.com/simsimmabimma/three-rising-valleys/refs/heads/main/nasdaqlisted%20-%20Sheet1.csv"
BATCH_SIZE = 100
THROTTLE_RANGE = (2, 5)  # seconds to sleep between batches
FIELDS_TO_EXTRACT = ['symbol', 'shortName', 'currentPrice', 'marketCap', 'volume', 'trailingPE']

def batch_list(lst, batch_size):
    for i in range(0, len(lst), batch_size):
        yield lst[i:i + batch_size]

def fetch_batch_data(batch):
    tickers_str = ' '.join(batch)
    data = yf.Tickers(tickers_str).tickers
    results = []

    for ticker in batch:
        try:
            info = data[ticker].info
            row = {field: info.get(field) for field in FIELDS_TO_EXTRACT}
            row['symbol'] = ticker
            results.append(row)
        except Exception as e:
            st.warning(f"Error fetching {ticker}: {e}")
    return results

def main():
    st.title("Batch Ticker Scanner with Auto Throttling")

    st.write(f"Loading tickers from remote CSV URL:")
    st.write(CSV_URL)

    try:
        df = pd.read_csv(CSV_URL)
        # Use the first column as tickers (assumes first column is ticker)
        tickers = df.iloc[:, 0].dropna().unique().tolist()
    except Exception as e:
        st.error(f"Error loading CSV from URL: {e}")
        return

    st.write(f"Total tickers loaded: {len(tickers)}")

    if st.button("Start Batch Scan"):
        all_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, batch in enumerate(batch_list(tickers, BATCH_SIZE), start=1):
            status_text.text(f"Processing batch {i} of {((len(tickers) - 1) // BATCH_SIZE) + 1}...")
            batch_data = fetch_batch_data(batch)
            all_data.extend(batch_data)

            progress_bar.progress(min(i * BATCH_SIZE / len(tickers), 1.0))

            # Throttle
            sleep_time = random.uniform(*THROTTLE_RANGE)
            status_text.text(f"Sleeping for {sleep_time:.2f} seconds to avoid rate limits...")
            time.sleep(sleep_time)

        status_text.text("Done fetching data!")

        results_df = pd.DataFrame(all_data)
        st.dataframe(results_df)

        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download results as CSV",
            data=csv,
            file_name='yahoo_results.csv',
            mime='text/csv'
        )

if __name__ == '__main__':
    main()
