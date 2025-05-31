import streamlit as st
import boto3
import pandas as pd
import gzip
import shutil
import os
from botocore.config import Config

# --- Secrets: Store these in .streamlit/secrets.toml ---
POLYGON_ACCESS_KEY = st.secrets["POLYGON_S3_ACCESS_KEY"]
POLYGON_SECRET_KEY = st.secrets["POLYGON_S3_SECRET_KEY"]
S3_ENDPOINT = "https://files.polygon.io"
BUCKET_NAME = "flatfiles"

# --- Initialize S3 client ---
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

    # Extract the .gz
    with gzip.open(local_gz_path, 'rb') as f_in:
        with open(local_csv_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Clean up .gz
    os.remove(local_gz_path)
    return local_csv_path

def scan_for_three_rising_valleys(df, min_periods=3):
    """
    Scan for three rising swing lows.
    """
    result = []
    grouped = df.groupby("ticker")

    for ticker, group in grouped:
        group = group.sort_values("timestamp")
        lows = group["low"].rolling(window=3, center=True).apply(
            lambda x: x[1] if x[1] < x[0] and x[1] < x[2] else None
        ).dropna()

        # Get actual low values and compare for rising pattern
        swing_lows = group.loc[lows.index, ["timestamp", "low"]]
        if len(swing_lows) >= 3:
            last_3 = swing_lows.tail(3)
            if all(x < y for x, y in zip(last_3["low"], last_3["low"][1:])):
                result.append({
                    "ticker": ticker,
                    "low1": last_3["low"].iloc[0],
                    "low2": last_3["low"].iloc[1],
                    "low3": last_3["low"].iloc[2],
                    "date3": pd.to_datetime(last_3["timestamp"].iloc[2], unit='ms')
                })

    return pd.DataFrame(result)

def main():
    st.title("Three Rising Valleys Scanner (Polygon Flat Files)")

    data_type = 'bars_v1'  # Only use bars for HL scans
    year = st.selectbox("Year", list(range(2020, 2025))[::-1])
    month = st.selectbox("Month", [f"{i:02}" for i in range(1, 13)])
    day = st.selectbox("Day", [f"{i:02}" for i in range(1, 32)])

    prefix = f"us_stocks_sip/{data_type}/{year}/{month}/"
    st.write(f"Looking in: `{prefix}`")

    files = list_files(prefix)
    if not files:
        st.warning("No files found.")
        return

    filtered_files = [f for f in files if f"{year}-{month}-{day}" in f]
    if not filtered_files:
        st.warning("No files found for selected date.")
        return

    selected_file = st.selectbox("Select flat file", filtered_files)

    if st.button("Download & Run Scan"):
        with st.spinner("Downloading and processing..."):
            local_csv = download_and_extract_s3_file(selected_file)
            df = pd.read_csv(local_csv)
            os.remove(local_csv)

            # Parse timestamp if present, else skip
            if 'timestamp' not in df.columns:
                st.error("This file doesn't contain time-series data with 'timestamp' column.")
                return

            df = df[["ticker", "timestamp", "low"]].dropna()
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')

            result_df = scan_for_three_rising_valleys(df)

        if not result_df.empty:
            st.success(f"Found {len(result_df)} tickers with rising valleys.")
            st.dataframe(result_df)
            csv = result_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download results as CSV", csv, "three_rising_valleys.csv", "text/csv")
        else:
            st.info("No valid rising valley patterns found.")

if __name__ == '__main__':
    main()
