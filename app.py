import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# Hardcoded tickers for testing
TICKERS = ["TARA", "SOFI"]

def find_swing_higher_lows(df, lookback_months=18, recent_low_months=3):
    if df.empty or len(df) < 10:
        return False, "Not enough data"

    df = df.sort_index()
    last_date = df.index[-1]
    start_date = last_date - pd.DateOffset(months=lookback_months)
    df = df[df.index >= start_date]

    lows = df['Low'].values
    highs = df['High'].values
    dates = df.index.to_list()
    n = len(df)

    swing_lows = []
    swing_highs = []

    i = 0
    while i < n - 1:
        low_val = lows[i]
        low_date = dates[i]

        high_idx = None
        for j in range(i + 1, n):
            if highs[j] > highs[j - 1]:
                high_idx = j
            else:
                break

        if high_idx is None or high_idx >= n:
            break

        high_val = highs[high_idx]
        high_date = dates[high_idx]

        retrace_idx = None
        for k in range(high_idx + 1, n):
            if lows[k] < lows[k - 1]:
                retrace_idx = k
                break

        if retrace_idx is None or retrace_idx >= n:
            break

        retr_low = lows[retrace_idx]
        retr_low_date = dates[retrace_idx]

        retracement = (high_val - retr_low) / (high_val - low_val)
        if retracement < 0.38:
            i = retrace_idx + 1
            continue

        swing_lows.append((low_date, low_val))
        swing_lows.append((retr_low_date, retr_low))
        swing_highs.append((high_date, high_val))

        if len(swing_lows) >= 2:
            recent_cutoff = last_date - pd.DateOffset(months=recent_low_months)
            if retr_low_date >= recent_cutoff:
                return True, f"Found pattern: last higher low at {retr_low_date.date()} retraced {retracement:.3f}"

        i = retrace_idx + 1

    return False, "Pattern not found"

def main():
    st.title("Swing Higher Lows Scanner (Monthly Chart)")

    tickers = TICKERS
    st.write(f"Testing with {len(tickers)} hardcoded tickers: {', '.join(tickers)}")

    if 'index' not in st.session_state:
        st.session_state.index = 0
    if 'found_tickers' not in st.session_state:
        st.session_state.found_tickers = []

    if st.session_state.index >= len(tickers):
        st.write("All tickers scanned.")
        if st.session_state.found_tickers:
            st.write("Tickers matching pattern:")
            for t, msg in st.session_state.found_tickers:
                st.write(f"- {t}: {msg}")
        return

    current_ticker = tickers[st.session_state.index]
    st.write(f"Scanning ticker {st.session_state.index + 1}/{len(tickers)}: **{current_ticker}**")

    if st.button("Scan This Ticker"):
        try:
            data = yf.Ticker(current_ticker).history(period="5y", interval="1mo")
            if data.empty:
                st.warning("No monthly data found.")
            else:
                found, msg = find_swing_higher_lows(data)
                if found:
                    st.success(f"{current_ticker} matches pattern! {msg}")
                    st.session_state.found_tickers.append((current_ticker, msg))
                else:
                    st.info(f"{current_ticker} does NOT match pattern. {msg}")
        except Exception as e:
            st.error(f"Error scanning {current_ticker}: {e}")

    if st.button("Next Ticker"):
        st.session_state.index += 1
        st.experimental_rerun()

    if st.session_state.found_tickers:
        st.write("Tickers found so far:")
        for t, msg in st.session_state.found_tickers:
            st.write(f"- {t}: {msg}")

if __name__ == "__main__":
    main()
