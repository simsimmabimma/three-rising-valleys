import streamlit as st
import duckdb
import pandas as pd
import boto3
from botocore.config import Config
import io
import zstandard as zstd
import json

# AWS config from secrets
aws_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret = st.secrets["aws"]["aws_secret_access_key"]

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

# Connect to DuckDB
con = duckdb.connect("stock_data.duckdb")

# Create OHLC table if it doesn't exist
con.execute("""
CREATE TABLE IF NOT EXISTS ohlc (
    ticker VARCHAR,
    timestamp DATE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT
)
""")

# 📁 List available flat files in S3
def list_files():
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith((".csv", ".json", ".csv.zst")):
                keys.append(key)
    return sorted(keys)

# 📄 Load a file from S3 and return as DataFrame
def load_file_from_s3(key):
    st.info(f"Loading: {key}")
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    raw = obj["Body"].read()

    try:
        if key.endswith(".csv"):
            return pd.read_csv(io.BytesIO(raw))
        elif key.endswith(".json"):
            data = json.loads(raw)
            return pd.DataFrame(data["results"] if "results" in data else data)
        elif key.endswith(".csv.zst"):
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.decompress(raw)
            return pd.read_csv(io.BytesIO(decompressed))
    except Exception as e:
        st.error(f"Failed to load {key}: {e}")
        return None

# 📥 Ingest file into DuckDB with deduplication
def ingest_file(key):
    df = load_file_from_s3(key)
    if df is None:
        return

    df.columns = [c.strip().lower() for c in df.columns]
    required = {"ticker", "timestamp", "open", "high", "low", "close", "volume"}

    if not required.issubset(set(df.columns)):
        st.warning(f"Skipping {key}: Missing columns: {required - set(df.columns)}")
        return

    df = df[list(required)].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.date

    new_rows = []
    check_query = "SELECT 1 FROM ohlc WHERE ticker = ? AND timestamp = ? LIMIT 1"

    for _, row in df.iterrows():
        if not con.execute(check_query, (row["ticker"], row["timestamp"])).fetchone():
            new_rows.append(row)

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        con.execute("INSERT INTO ohlc SELECT * FROM new_df")
        st.success(f"✅ Ingested {len(new_df)} new rows from {key}")
    else:
        st.info(f"✅ {key}: No new rows — already ingested.")

# 📊 Higher swing low scan
def find_higher_swing_lows(df: pd.DataFrame) -> pd.DataFrame:
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["ticker", "timestamp"])
    results = []

    for ticker, group in df.groupby("ticker"):
        monthly = group.set_index("timestamp").resample("M").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna()

        lows = monthly["low"].values
        closes = monthly["close"].values
        if len(lows) < 24:
            continue

        for i in range(1, len(lows)):
            if lows[i] > lows[i - 1] and closes[-1] > lows[i]:
                results.append({
                    "ticker": ticker,
                    "swing_low_1": lows[i - 1],
                    "swing_low_2": lows[i],
                    "current_close": closes[-1],
                    "date_of_higher_low": monthly.index[i].strftime("%Y-%m-%d"),
                })
                break

    return pd.DataFrame(results)

# ---------- STREAMLIT UI ----------
st.title("📈 Three Rising Valleys: Flat File Scanner")

st.header("📥 Ingest Historical OHLC File")
files = list_files()
selected_file = st.selectbox("Choose file to ingest from S3:", files)

if st.button("Ingest selected file"):
    ingest_file(selected_file)

st.divider()

st.header("🔍 Scan for Higher Swing Lows")
df = con.execute("SELECT * FROM ohlc").df()

if df.empty:
    st.warning("No data yet. Please ingest a file first.")
else:
    if st.button("Run scan"):
        with st.spinner("Scanning..."):
            result_df = find_higher_swing_lows(df)
        st.success(f"✅ Found {len(result_df)} matching tickers")
        st.dataframe(result_df)

        st.download_button("⬇️ Download CSV", result_df.to_csv(index=False), "scan_results.csv")
