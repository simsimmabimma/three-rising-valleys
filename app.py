import streamlit as st
import pandas as pd
import boto3
from datetime import datetime
import re

# 1️⃣ Must be first Streamlit command
st.set_page_config(page_title="Swing Low Stock Scanner", layout="wide")

def get_s3_file_stream(bucket, key):
    session = boto3.Session(
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_DEFAULT_REGION"]
    )
    s3 = session.client('s3')
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj['Body']

def run_swing_low_analysis(df, cols):
    # Sort and parse date
    df = df.sort_values([cols['ticker'], cols['timestamp']])
    df[cols['timestamp']] = pd.to_datetime(df[cols['timestamp']])
    df.set_index(cols['timestamp'], inplace=True)

    # Resample monthly lows and closes per symbol
    low_series = df.groupby(cols['ticker'])[cols['low']].resample('M').min().reset_index()
    close_series = df.groupby(cols['ticker'])[cols['close']].resample('M').last().reset_index()

    monthly = pd.merge(low_series, close_series, on=[cols['ticker'], cols['timestamp']],
                       suffixes=('_low', '_close'))

    today = pd.to_datetime('today').normalize()
    three_months_ago = today - pd.DateOffset(months=3)
    six_months_ago = today - pd.DateOffset(months=6)

    recent = monthly[(monthly[cols['timestamp']] >= six_months_ago) & (monthly[cols['timestamp']] <= three_months_ago)]

    results = []

    for symbol in recent[cols['ticker']].unique():
        sub = recent[recent[cols['ticker']] == symbol]
        swing_low = sub[cols['low'] + '_low'].min()
        swing_low_date = sub[sub[cols['low'] + '_low'] == swing_low][cols['timestamp']].values[0]

        # Get most recent close from original df
        recent_close = df[df[cols['ticker']] == symbol].reset_index().sort_values(cols['timestamp']).iloc[-1][cols['close']]

        if recent_close > swing_low:
            results.append({
                'symbol': symbol,
                'swing_low': swing_low,
                'swing_low_date': pd.to_datetime(swing_low_date),
                'recent_close': recent_close
            })

    return pd.DataFrame(results)

def main():
    st.title("📈 Swing Low Stock Scanner")

    bucket = st.text_input("S3 Bucket", value="your-bucket-name")
    key = st.text_input("S3 Key (CSV file)", value="xnas-itch-20200531-20250530.ohlcv-1d.0000.csv")

    if st.button("Load CSV Columns"):
        try:
            stream = get_s3_file_stream(bucket, key)
            df_sample = pd.read_csv(stream, nrows=5)
            columns = list(df_sample.columns)
            st.success("Columns loaded successfully!")
            st.write("Sample data:")
            st.dataframe(df_sample)

            # Store columns in session_state for dropdowns
            st.session_state['columns'] = columns
            st.session_state['bucket'] = bucket
            st.session_state['key'] = key

        except Exception as e:
            st.error(f"Failed to load CSV: {e}")

    if 'columns' in st.session_state:
        st.markdown("### Map your CSV columns")
        cols = st.session_state['columns']

        ticker_col = st.selectbox("Select the Ticker column", cols)
        timestamp_col = st.selectbox("Select the Timestamp/Date column", cols)
        open_col = st.selectbox("Select the Open price column", cols)
        high_col = st.selectbox("Select the High price column", cols)
        low_col = st.selectbox("Select the Low price column", cols)
        close_col = st.selectbox("Select the Close price column", cols)

        if st.button("Run Analysis"):
            with st.spinner("Loading full CSV and analyzing... This may take a while for large files."):

                try:
                    stream = get_s3_file_stream(st.session_state['bucket'], st.session_state['key'])
                    df_full = pd.read_csv(stream)

                    # Check that selected columns exist
                    for c in [ticker_col, timestamp_col, open_col, high_col, low_col, close_col]:
                        if c not in df_full.columns:
                            st.error(f"Column '{c}' not found in CSV!")
                            return

                    col_map = {
                        'ticker': ticker_col,
                        'timestamp': timestamp_col,
                        'open': open_col,
                        'high': high_col,
                        'low': low_col,
                        'close': close_col
                    }

                    result_df = run_swing_low_analysis(df_full, col_map)

                    if result_df.empty:
                        st.info("No stocks matched the swing low criteria in the selected timeframe.")
                    else:
                        st.success(f"Found {len(result_df)} stocks matching criteria:")
                        st.dataframe(result_df)

                        csv = result_df.to_csv(index=False).encode('utf-8')
                        st.download_button("Download Results CSV", csv, "swing_low_results.csv")

                except Exception as e:
                    st.error(f"Error during analysis: {e}")

if __name__ == "__main__":
    main()
