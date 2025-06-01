import boto3
import pandas as pd
import zstandard as zstd
import io
import duckdb
import streamlit as st

# Load secrets from .streamlit/secrets.toml
aws_key = st.secrets["aws"]["aws_access_key_id"]
aws_secret = st.secrets["aws"]["aws_secret_access_key"]
endpoint_url = "https://s3.amazonaws.com"  # or use polygon endpoint if needed
bucket_name = "flatfiles"

# Connect to S3
s3 = boto3.client(
    "s3",
    aws_access_key_id=aws_key,
    aws_secret_access_key=aws_secret,
    endpoint_url=endpoint_url
)

# Connect to DuckDB
con = duckdb.connect("stock_data.duckdb")
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

# Load and parse one file from S3
def load_file_from_s3(key):
    print(f"Loading: {key}")
    obj = s3.get_object(Bucket=bucket_name, Key=key)
    data = obj["Body"].read()

    if key.endswith(".csv.zst"):
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(data)
        df = pd.read_csv(io.BytesIO(decompressed))
    elif key.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(data))
    elif key.endswith(".json"):
        df = pd.read_json(io.BytesIO(data), lines=True)
    else:
        print("Unsupported file format:", key)
        return None

    return df

# Ingest a specific file into DuckDB
def ingest_file(key):
    df = load_file_from_s3(key)
    if df is not None:
        df.columns = [col.strip().lower() for col in df.columns]
        required_cols = {"ticker", "timestamp", "open", "high", "low", "close", "volume"}
        if required_cols.issubset(set(df.columns)):
            con.execute("INSERT INTO ohlc SELECT * FROM df")
            st.success(f"✅ Ingested {key}")
        else:
            st.warning(f"⚠️ Skipped {key} — missing required columns")

# Streamlit UI
st.title("📦 Stock OHLC Ingestor (S3 → DuckDB)")

# List files in S3
response = s3.list_objects_v2(Bucket=bucket_name, Prefix="ohlc/")
keys = [obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith((".csv", ".json", ".csv.zst"))]

selected_files = st.multiselect("Select files to ingest:", options=keys)

if st.button("🚀 Ingest Selected Files"):
    for key in selected_files:
        ingest_file(key)

if st.button("🗃️ Show Table Sample"):
    st.dataframe(con.execute("SELECT * FROM ohlc LIMIT 20").df())
