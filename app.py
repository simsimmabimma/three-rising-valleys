import streamlit as st
import pandas as pd
import boto3
from io import BytesIO
import re
from datetime import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Swing Low Stock Scanner", layout="wide")
st.title("📉 Monthly Swing Low Scanner (3–6 Months)")

# ---------- S3 FILE DOWNLOAD ----------
def get_s3_file(bucket, key):
    session = boto3.Session()
    s3 = session.client('s3')
    obj = s3.get_object(Bucket=bucket, Key=key)
    return BytesIO(obj['Body'].read())

# ---------- COLUMN INFERENCE ----------
def infer_columns(df):
    col_map = {}
    for col in df.columns:
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

# ---------- SWING LOW ANALYSIS ----------
def find_swing_lows(df, col_map):
    df[col_map['date']] = pd.to_datetime(df[col_map['date']])
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

# ---------- STREAMLIT UI ----------
with st.sidebar:
    st.header("📁 Load Data from S3")
    s3_bucket = st.text_input("S3 Bucket", value="your-bucket-name")  # ⬅️ Replace with your bucket name
    s3_key = st.text_input("S3 Key (CSV File)", value="xnas-itch-20200531-20250530.ohlcv-1d.0000.csv")

    if st.button("🔍 Load and Analyze"):
        try:
            st.info("📦 Downloading and analyzing data...")
            data = get_s3_file(s3_bucket, s3_key)
            df = pd.read_csv(data)

            st.success("✅ CSV loaded successfully.")
            col_map = infer_columns(df)

            st.info("🔍 Running swing low analysis...")
            result_df = find_swing_lows(df, col_map)

            st.success("✅ Analysis complete.")
            st.dataframe(result_df)

            csv = result_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results as CSV", data=csv, file_name="swing_low_results.csv")

        except Exception as e:
            st.error(f"❌ Error: {e}")
