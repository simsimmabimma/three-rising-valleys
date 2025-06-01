import streamlit as st
import boto3
from botocore.config import Config
import pandas as pd
import duckdb
import io
import zstandard as zstd
import json

# Setup AWS credentials from Streamlit secrets
aws_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret = st.secrets["aws"]["aws_secret_access_key"]

# Initialize boto3 S3 client
session = boto3.Session(
    aws_access_key_id=aws_key,
    aws_secret_access_key=aws_secret,
)
s3 = session.client(
    "s3",
    endpoint_url="https://files.polygon.io",
    config=Config(signature_version="s3v4"),
)

BUCKET = "ohlcfile"
PREFIX = "us_stocks_sip/"

# Connect to DuckDB or create if it doesn't exist
con = duckdb.connect("stock_data.duckdb")
con.execute(
    """
    CREATE TABLE IF NOT EXISTS ohlc (
        ticker VARCHAR,
        timestamp DATE,
        open DOUBLE,
        high DOUBLE,
        low DOUBLE,
        close DOUBLE,
        volume BIGINT
    )
"""
)

st.title("Polygon Flat Files Ingestion with Deduplication")

# List files in S3 under prefix
def list_files():
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith((".csv", ".json", ".csv.zst")):
                keys.append(key)
    return keys

# Load file from S3 and return pandas DataFrame
def load_file_from_s3(key):
    st.info(f"Loading {key} ...")
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    raw = obj["Body"].read()

    try:
        if key.endswith(".csv"):
            return pd.read_csv(io.BytesIO(raw))
        elif key.endswith(".json"):
            data = json.loads(raw)
            # Assuming data is a list of dicts or dict with "results" key
            if isinstance(data, dict) and "results" in data:
                return pd.DataFrame(data["results"])
            else:
                return pd.DataFrame(data)
        elif key.endswith(".csv.zst"):
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.decompress(raw)
            return pd.read_csv(io.BytesIO(decompressed))
    except Exception as e:
        st.error(f"Failed to load {key}: {e}")
        return None

def ingest_file(key):
    df = load_file_from_s3(key)
    if df is None:
        return

    # Normalize columns
    df.columns = [col.strip().lower() for col in df.columns]

    required_cols = {"ticker", "timestamp", "open", "high", "low", "close", "volume"}
    if not required_cols.issubset(set(df.columns)):
        st.warning(f"Skipped {key} — missing required columns: {required_cols - set(df.columns)}")
        return

    df = df[list(required_cols)].copy()

    # Convert timestamp to date only (no time)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.date

    # Deduplication logic: Check which rows are already in DuckDB
    unique_rows = []
    existing_check_q = "SELECT 1 FROM ohlc WHERE ticker = ? AND timestamp = ? LIMIT 1"

    for idx, row in df.iterrows():
        exists = con.execute(existing_check_q, (row["ticker"], row["timestamp"])).fetchone()
        if not exists:
            unique_rows.append(row)

    if not unique_rows:
        st.info(f"All rows in {key} already exist in database, skipping insert.")
        return

    new_df = pd.DataFrame(unique_rows)
    con.execute("INSERT INTO ohlc SELECT * FROM new_df")

    st.success(f"Ingested {len(new_df)} new rows from {key}")

def main():
    files = list_files()
    st.write(f"Found {len(files)} files in S3 under `{PREFIX}`")

    file_to_ingest = st.selectbox("Select a file to ingest:", files)
    if st.button("Ingest selected file"):
        ingest_file(file_to_ingest)

    # Show count of rows in DB
    count = con.execute("SELECT COUNT(*) FROM ohlc").fetchone()[0]
    st.write(f"Total rows in DuckDB: {count}")

if __name__ == "__main__":
    main()
