import streamlit as st
import yfinance as yf
import math
from datetime import datetime

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
        print(f"Not enough monthly data for {ticker}")
        return False
    
    lows = data['Low'].tolist()
    highs = data['High'].tolist()
    dates = data.index.tolist()

    print(f"Monthly lows for {ticker}:")
    for d, low in zip(dates, lows):
        print(f"{d.strftime('%Y-%m')}: {low}")

    # Find swing low - the lowest low in the dataset
    swing_low = min(lows)
    swing_low_idx = lows.index(swing_low)
    print(f"Swing low: {swing_low} at {dates[swing_low_idx].strftime('%Y-%m')}")

    # Find swing high after swing low
    highs_after_low = highs[swing_low_idx + 1 :]
    if not highs_after_low:
        print("No data after swing low to find swing high")
        return False

    swing_high = max(highs_after_low)
    swing_high_idx = highs_after_low.index(swing_high) + swing_low_idx + 1
    print(f"Swing high: {swing_high} at {dates[swing_high_idx].strftime('%Y-%m')}")

    # Calculate 0.618 retracement on log scale
    retrace_price = log_fib_0618(swing_low, swing_high)
    print(f"0.618 Fib Retracement price (log scale): {retrace_price}")

    # Check last 3 months lows if dipped to or below retracement price
    last_3_lows = lows[-3:]
    last_3_dates = dates[-3:]
    print("Checking last 3 months lows vs retracement price:")
    for d, low in zip(last_3_dates, last_3_lows):
        print(f"{d.strftime('%Y-%m')}: low={low}")
        if low <= retrace_price:
            print(f"Retracement dip detected in {d.strftime('%Y-%m')} with low {low} <= {retrace_price}")
            return True

    print("No retracement dip detected in last 3 months.")
    return False

check_retracement_sofi()
