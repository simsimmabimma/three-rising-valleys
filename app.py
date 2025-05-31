import streamlit as st
import boto3
import pandas as pd
import gzip
import shutil
import os
from botocore.config import Config
from datetime import datetime, timedelta

# --- Secrets ---
POLYGON_ACCESS_KEY = st.secrets["POLYGON_S3_ACCESS_KEY"]
POLYGON_SECRET_KEY = st.secrets["POLYGON_S3_SECRET_KEY"]
S3_ENDPOINT = "https://files.polygon.io"
BUCKET_NAME = "flatfiles"

# --- S3 Setup ---
session = boto3.Session(
    aws_access_key_id=POLYGON_ACCESS_KEY,
    aws_secret_access_key=POLYGON_SECRET_KEY,
)

s3 = session.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    config=Config(signature_version='s3v4'),
)

def list_files(prefix):
    paginator = s3.get_paginator('list_objects_v2')
    files = []
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        files.extend([obj['Key'] for obj in page.get('Contents', [])])
    return files

def download_and_extract_s3_file(object_key):
    local_gz_path = object_key.split('/')[-1]
    local_csv_path = local_gz_path.replace('.gz', '')

    # Download from S3
    s3.download_file(BUCKET_NAME, object_key, local_gz_path)

    # Extract
    with gzip.open(local_gz_path, 'rb') as f_in:
        with open(local_csv_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    os.remove(local_gz_path)
    return local_csv_path

def find_swing_lows(prices):
    """
    Find swing lows (local minima) from a price Series
    """
    return [
        (i, prices[i])
        for i in range(1, len(prices) - 1)
        if prices[i] < prices[i - 1] and prices[i] < prices[i + 1]
    ]

def meets_criteria(df):
    """
    Check if ticker has a higher low and is trading above it
    """
    df = df.sort_values("timestamp")
    df.set_index("timestamp", inplace=True)
    monthly = df.resample("M").agg({"low": "min", "close": "last"}).dropna()

    if len(monthly) < 6:
        return False

    swing_lows = find_swing_lows(monthly["low"].tolist())

    if len(swing_lows) < 2:
        return False

    # Take last two swing lows
    i1, low1 = swing_lows[-2]
    i2, low2 = swing_lows[-1]

    if low2 > low1:
        current_close = monthly["close"].iloc[-1]
        return current_close > low2

    return False

def main():
    st.title("Monthly Higher Low Scanner (Polygon Flat Files)")
    st.markdown("Scan tickers from Polygon S3 flat files for higher swing lows on monthly charts.")

    # Download and combine data for the last 24 months
    st.info("This may take a while. Processing ~24 monthly files.")

    with st.spinner("Fetching files from Polygon..."):
        today = datetime.utcnow()
        results = []
        all_data = []

        # Load last 24 months of bars_v1
        for i in range(24):
            date = today - pd.DateOffset(months=i)
            y, m = date.year, f"{date.month:02}"
            prefix = f"us_stocks_sip/bars_v1/{y}/{m}/"

            files = list_files(prefix)
            if not files:
                continue

            # We use only 1 file per month, e.g., the first one (there may be one per ticker)
            for file in files:
                if not file.endswith(".csv.gz"):
                    continue
                try:
                    path = download_and_extract_s3_file(file)
                    df = pd.read_csv(path)
                    os.remove(path)
                    df = df[["ticker", "timestamp", "low", "close"]]
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    all_data.append(df)
                    break  # Just 1 file per month for now
                except Exception as e:
                    st.warning(f"Error with file {file}: {e}")
                    continue

        if not all_data:
            st.error("No data could be loaded.")
            return

        full_df = pd.concat(all_data)

        tickers = full_df["ticker"].unique()
        st.write(f"Processing {len(tickers)} tickers...")

        for ticker in tickers:
            data = full_df[full_df["ticker"] == ticker]
            if meets_criteria(data):
                results.append(ticker)

    if results:
        st.success(f"Found {len(results)} tickers meeting the pattern!")
        st.dataframe(pd.DataFrame(results, columns=["Ticker"]))
        st.download_button("Download CSV", pd.DataFrame(results).to_csv(index=False), "higher_lows.csv", "text/csv")
    else:
        st.info("No tickers met the criteria.")

if __name__ == "__main__":
    main()
