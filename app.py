import streamlit as st
import pandas as pd
import boto3

import traceback

try:
    # Your entire app code here (or just call main())
    if __name__ == "__main__":
        main()
except Exception as e:
    st.error("❌ Error running app:")
    st.text(traceback.format_exc())

from io import BytesIO, StringIO
import re
from datetime import datetime



st.set_page_config(page_title="Swing Low Stock Scanner", layout="wide")
st.title("📉 Monthly Swing Low Scanner (3–6 Months)")

# ---------- COLUMN INFERENCE ----------
def infer_columns(columns):
    col_map = {}
    for col in columns:
        col_l = col.lower()
        if 'symbol' in col_l or 'ticker' in col_l:
            col_map['symbol'] = col
        elif re.search(r'date|time', col_l):
            col_map['date'] = col
        elif 'open' in col_l:
            col_map['open'] = col
        elif 'high' in col_l:
            col_map['high'] = col
        elif 'low' in col_l:
            col_map['low'] = col
        elif 'close' in col_l:
            col_map['close'] = col

    required = ['symbol', 'date', 'open', 'high', 'low', 'close']
    missing = [col for col in required if col not in col_map]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return col_map

# ---------- Get S3 file stream ----------
def get_s3_file_stream(bucket, key):
    session = boto3.Session(
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_DEFAULT_REGION"]
    )
    s3 = session.client('s3')
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj['Body']

# ---------- Main App ----------
def main():
    with st.sidebar:
        st.header("📁 Load Data from S3")
        s3_bucket = st.text_input("S3 Bucket", value="your-bucket-name")
        s3_key = st.text_input("S3 Key (CSV File)", value="xnas-itch-20200531-20250530.ohlcv-1d.0000.csv")
        analyze_btn = st.button("🔍 Load and Analyze")

    if analyze_btn:
        try:
            status_text = st.empty()
            scanned_text = st.empty()
            matched_text = st.empty()

            status_text.info("Connecting to S3 and opening file...")

            stream = get_s3_file_stream(s3_bucket, s3_key)

            status_text.info("Reading CSV headers to infer columns...")

            # Read just the first chunk for columns inference
            sample_df = pd.read_csv(stream, nrows=1000)
            col_map = infer_columns(sample_df.columns)

            status_text.success(f"Columns inferred: {col_map}")

            # Restart stream for full read because the stream is already partially read
            stream = get_s3_file_stream(s3_bucket, s3_key)

            chunk_size = 100_000  # tune if needed
            reader = pd.read_csv(stream, chunksize=chunk_size)

            # Dataframes to accumulate chunks (be mindful of memory!)
            all_data = []

            tickers_scanned = set()
            tickers_matched = []

            status_text.info(f"Start ingesting and scanning data in chunks of {chunk_size} rows...")

            for i, chunk in enumerate(reader):
                # Infer columns for this chunk just to be safe (skip if sure columns are consistent)
                # chunk.columns = col_map.values()

                # Append to accumulator
                all_data.append(chunk)

                # Track scanned tickers
                tickers_scanned.update(chunk[col_map['symbol']].unique())

                # Combine all_data so far for analysis (may be heavy for large files)
                df = pd.concat(all_data)

                # Convert date column to datetime
                df[col_map['date']] = pd.to_datetime(df[col_map['date']])

                # Run swing low analysis on accumulated data
                matched_df = run_swing_low_analysis(df, col_map)

                tickers_matched = matched_df['symbol'].tolist()

                status_text.info(f"Processed chunk {i+1}...")

                scanned_text.markdown(f"**Tickers scanned so far:** {', '.join(sorted(tickers_scanned))}")
                matched_text.markdown(f"**Tickers matching criteria:** {', '.join(sorted(tickers_matched))}")

            status_text.success("✅ Finished scanning all chunks.")
            st.dataframe(matched_df)

            csv = matched_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results as CSV", data=csv, file_name="swing_low_results.csv")

        except Exception as e:
            st.error(f"Error: {e}")

def run_swing_low_analysis(df, col_map):
    df = df.sort_values([col_map['symbol'], col_map['date']])
    df.set_index(col_map['date'], inplace=True)

    low_series = df.groupby(col_map['symbol'])[col_map['low']].resample('M').min().reset_index()
    close_series = df.groupby(col_map['symbol'])[col_map['close']].resample('M').last().reset_index()

    monthly = pd.merge(low_series, close_series, on=[col_map['symbol'], col_map['date']],
                       suffixes=('_low', '_close'))

    today = pd.to_datetime('today').normalize()
    three_months_ago = today - pd.DateOffset(months=3)
    six_months_ago = today - pd.DateOffset(months=6)

    recent = monthly[(monthly[col_map['date']] >= six_months_ago) & (monthly[col_map['date']] <= three_months_ago)]

    results = []

    for symbol in recent[col_map['symbol']].unique():
        sub = recent[recent[col_map['symbol']] == symbol]
        swing_low = sub[col_map['low'] + '_low'].min()
        swing_low_date = sub[sub[col_map['low'] + '_low'] == swing_low][col_map['date']].values[0]

        # Get most recent close
        recent_close = df[df[col_map['symbol']] == symbol].reset_index().sort_values(col_map['date']).iloc[-1][col_map['close']]

        if recent_close > swing_low:
            results.append({
                'symbol': symbol,
                'swing_low': swing_low,
                'swing_low_date': pd.to_datetime(swing_low_date),
                'recent_close': recent_close
            })

    return pd.DataFrame(results)

if __name__ == "__main__":
    main()
