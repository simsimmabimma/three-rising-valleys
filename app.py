import streamlit as st
import yfinance as yf
import math
from datetime import datetime

st.title("Monthly 0.618 Retracement Scanner (Log Scale) - SOFI Test")

def log_fib_0618(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    log_retracement = log_high - 0.618 * log_diff
    return round(math.exp(log_retracement), 2)

def check_retracement_sofi():
    ticker = "SOFI"
    tk = yf.Ticker(ticker)
    data = tk.history(period="2y", interval="1mo")

    if data.empty or len(data) < 6:
        st.write(f"Not enough monthly data for {ticker}")
        return False
    
    lows = data['Low'].tolist()
    highs = data['High'].tolist()
    dates = data.index.tolist()

    st.write(f"Monthly lows for {ticker}:")
    for d, low in zip(dates, lows):
        st.write(f"{d.strftime('%Y-%m')}: {low}")

    swing_low = min(lows)
    swing_low_idx = lows.index(swing_low)
    st.write(f"Swing low: {swing_low} at {dates[swing_low_idx].strftime('%Y-%m')}")

    highs_after_low = highs[swing_low_idx + 1 :]
    if not highs_after_low:
        st.write("No data after swing low to find swing high")
        return False

    swing_high = max(highs_after_low)
    swing_high_idx = highs_after_low.index(swing_high) + swing_low_idx + 1
    st.write(f"Swing high: {swing_high} at {dates[swing_high_idx].strftime('%Y-%m')}")

    retrace_price = log_fib_0618(swing_low, swing_high)
    st.write(f"0.618 Fib Retracement price (log scale): {retrace_price}")

    last_3_lows = lows[-3:]
    last_3_dates = dates[-3:]
    st.write("Checking last 3 months lows vs retracement price:")
    for d, low in zip(last_3_dates, last_3_lows):
        st.write(f"{d.strftime('%Y-%m')}: low={low}")
        if low <= retrace_price:
            st.success(f"Retracement dip detected in {d.strftime('%Y-%m')} with low {low} ≤ {retrace_price}")
            return True

    st.info("No retracement dip detected in last 3 months.")
    return False

if st.button("Check SOFI"):
    result = check_retracement_sofi()
    if result:
        st.write("Pattern found for SOFI.")
    else:
        st.write("No pattern found for SOFI.")

