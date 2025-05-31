import streamlit as st
import requests
import math
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("A_xj1Mwz42bTgVFi6Hz0gOEm4Olk9aDH")
BASE_URL = "https://api.polygon.io"

st.title("📉 Test 0.618 Retracement Scanner on SOFI (Log Scale)")

@st.cache_data(ttl=3600)
def get_monthly_data(ticker, to="2025-04-30"):
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/month/2015-01-01/{to}?adjusted=true&sort=asc&apiKey={API_KEY}"
    resp = requests.get(url)
    data = resp.json().get("results", [])
    st.write(f"Fetched {len(data)} monthly candles for {ticker}")
    return data

def log_fib_0618(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    log_retracement = log_high - 0.618 * log_diff
    return round(math.exp(log_retracement), 2)

def scan_ticker(ticker):
    data = get_monthly_data(ticker)
    if len(data) < 18:
        st.write("Not enough monthly data.")
        return False

    prices = [{"date": datetime.utcfromtimestamp(candle["t"] / 1000), "low": candle["l"], "high": candle["h"], "close": candle["c"]} for candle in data]
    recent = prices[-18:]  # last 18 months

    st.write("Last 18 months data:")
    for d in recent:
        st.write(f"{d['date'].strftime('%b %Y')}: low={d['low']}, high={d['high']}, close={d['close']}")

    local_low = min(recent, key=lambda x: x["low"])
    low_index = recent.index(local_low)
    st.write(f"Local low: {local_low['low']} at {local_low['date'].strftime('%b %Y')} (index {low_index})")

    if low_index == len(recent) - 1:
        st.write("Local low is last month, no data after for high.")
        return False

    subsequent = recent[low_index + 1:]
    local_high = max(subsequent, key=lambda x: x["high"])
    high_index = recent.index(local_high)
    st.write(f"Local high: {local_high['high']} at {local_high['date'].strftime('%b %Y')} (index {high_index})")

    if high_index <= low_index:
        st.write("Invalid sequence: high comes before low.")
        return False

    retrace_price = log_fib_0618(local_low["low"], local_high["high"])
    st.write(f"Calculated 0.618 log fib retracement price: {retrace_price}")

    for month_data in recent[high_index + 1:]:
        st.write(f"Checking month {month_data['date'].strftime('%b %Y')} low_
