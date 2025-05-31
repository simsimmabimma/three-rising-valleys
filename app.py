import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# Hardcoded tickers for testing
TICKERS = ["TARA", "SOFI"]

def has_higher_low_last_24_months(df):
    if df.empty or len(df) < 26:
        return False, "Not enough monthly data (need at least 26 months)"

    df = df.sort_index()
    df = df[df.index >= df.index[-1] - pd.DateOffset(months=25)]

    lows = df['Low'].values
    closes = df['Close'].values
    dates = df.index.to_list()
    n = len(df)

    local_lows = []

    for i in range(1, n - 1):
        if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            local_lows.append((dates[i], lows[i]))

    if len(local_lows) < 2:
        return False, "Not enough local lows found"

    for i in range(1, len(local_lows)):
        prev_date, prev_low = local_lows[i - 1]
        curr_date, curr_low = local_lows[i]

        if curr_low > prev_low and curr_date >= df.index[-1] - pd.DateOffset(months=24):
            latest_close = closes[-1]
            if latest_close > curr_low:
                return True, f"Higher low on {curr_date.date()} (prev: {prev_date.date()}), latest close {latest_close:.2f} > low {curr_low:.2f}"
            else:
                return False, f"Higher low on {curr_date.date()}, but latest close ({latest_close:.2f}) is not higher than low ({curr_low:.2f})"

    return False, "No higher low in the last 24 months"

def main():
    st.title("Higher Low + Price Above Low (Monthly Chart - Last 24 Months)")

    tickers = TICKERS
    st.write(f"Testing with {len(tickers)} hardcoded tickers: {', '.join(tickers)}")

    if 'index' not in st.session_state:
        st.session_state.index = 0
    if 'found_tickers' not in st.session_state:
        st.session_state.found_tickers = []

    if st.session_state.index >= len(tickers):
        st.success("✅ All tickers scanned.")
        if st.session_state.found_tickers:
            st.subheader("Tickers matching pattern:")
            for t, msg in st.session_state.found_tickers:
                st.write(f"- {t}: {msg}")
        else:
            st.info("No tickers matched the pattern.")
        return

    current_ticker = tickers[st.session_state.index]
    st.header(f"Scanning {current_ticker} ({st.session_state.index + 1} of {len(tickers)})")

    scan_ticker_clicked = st.button("🔍 Scan This Ticker")
    next_ticker_clicked = st.button("➡️ Next Ticker")

    if scan_ticker_clicked:
        try:
            data = yf.Ticker(current_ticker).history(period="5y", interval="1mo")

            if data.empty:
                st.warning("No data returned from Yahoo Finance.")
                return

            if not {'High', 'Low', 'Close'}.issubset(data.columns):
                st.warning("Data missing required columns.")
                return

            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)

            found, msg = has_higher_low_last_24_months(data)
            if found:
                st.success(f"✅ {current_ticker} matches pattern! {msg}")
                st.session_state.found_tickers.append((current_ticker, msg))
            else:
                st.info(f"{current_ticker} does NOT match pattern. {msg}")

        except Exception as e:
            st.error(f"Error scanning {current_ticker}: {e}")

    if next_ticker_clicked:
        st.session_state.index += 1
        st.rerun()

    if st.session_state.found_tickers:
        st.write("✅ Tickers found so far:")
        for t, msg in st.session_state.found_tickers:
            st.write(f"- {t}: {msg}")

if __name__ == "__main__":
    main()
