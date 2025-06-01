import streamlit as st
import duckdb
import pandas as pd

st.title("Three Rising Valleys - Higher Swing Low Scanner")

# Connect to DuckDB
con = duckdb.connect("stock_data.duckdb")

# Load all OHLC data
df = con.execute("SELECT * FROM ohlc").df()

if df.empty:
    st.warning("No OHLC data found. Please ingest flat files first.")
    st.stop()

# Convert timestamp to datetime
df["timestamp"] = pd.to_datetime(df["timestamp"])

@st.cache_data
def find_higher_swing_lows(df: pd.DataFrame) -> pd.DataFrame:
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
        if len(lows) < 24:
            continue

        # Check for higher low pattern in last 24 months
        for i in range(1, len(lows)):
            if lows[i] > lows[i - 1] and monthly["close"].iloc[-1] > lows[i]:
                results.append({
                    "ticker": ticker,
                    "higher_low_date": monthly.index[i].strftime("%Y-%m-%d"),
                    "higher_low_value": lows[i],
                    "current_close": monthly["close"].iloc[-1],
                })
                break

    return pd.DataFrame(results)

if st.button("🔍 Scan for Higher Swing Lows"):
    with st.spinner("Scanning..."):
        results_df = find_higher_swing_lows(df)
        st.success(f"Found {len(results_df)} tickers with higher swing lows.")
        st.dataframe(results_df)

        csv = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download results CSV", csv, "higher_swing_lows.csv")

