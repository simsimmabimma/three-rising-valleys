import streamlit as st
import requests
import math
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("A_xj1Mwz42bTgVFi6Hz0gOEm4Olk9aDH")

BASE_URL = "https://api.polygon.io"

st.title("📉 Monthly 0.618 Retracement Scanner (Log Scale)")

def get_tickers(limit=200):
    url = f"{BASE_URL}/v3/reference/tickers?market=stocks&exchange=XNYS&active=true&limit={limit}&apiKey={API_KEY}"
    response = requests.get(url)
    results = response.json().get("results", [])
    return [t["ticker"] for t in results if "ticker" in t]

@st.cache_data(ttl=3600)
def get_monthly_data(ticker, to="2025-04-30"):
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/month/2015-01-01/{to}?adjusted=true&sort=asc&apiKey={API_KEY}"
    resp = requests.get(url)
    data = resp.json().get("results", [])
    return data

def log_fib_0618(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    log_retracement = log_high - 0.618 * log_diff
    return round(math.exp(log_retracement), 2)

def scan_ticker(ticker):
    data = get_monthly_data(ticker)
    if len(data) < 12:
        return False

    prices = [{"date": datetime.utcfromtimestamp(candle["t"] / 1000), "low": candle["l"], "high": candle["h"], "close": candle["c"]} for candle in data]
    recent = prices[-12:]

    local_low = min(recent[:-4], key=lambda x: x["low"])  # Allow 3+ months buffer
    low_index = recent.index(local_low)
    local_high = max(recent[low_index + 1:], key=lambda x: x["high"])
    high_index = recent.index(local_high)

    if high_index <= low_index:
        return False  # No valid swing

    retrace_price = log_fib_0618(local_low["low"], local_high["high"])

    latest = recent[-1]

    # CHANGE HERE: Check if latest month low dipped to or below 0.618 retracement price
    if latest["low"] <= retrace_price:
        return {
            "ticker": ticker,
            "low": local_low["low"],
            "high": local_high["high"],
            "retraced_low": latest["low"],
            "expected_0618": retrace_price,
            "month": latest["date"].strftime("%b %Y")
        }

    return False

def main():
    st.write("Scanning tickers... (this may take some time)")

    tickers = get_tickers(limit=200)  # Increase limit or paginate as needed

    matches = []
    progress = st.progress(0)

    for i, ticker in enumerate(tickers):
        result = scan_ticker(ticker)
        if result:
            matches.append(result)
        progress.progress((i+1)/len(tickers))

    st.success(f"Found {len(matches)} tickers with retracement dip.")
    for match in matches:
        st.write(match)

if __name__ == "__main__":
    main()
