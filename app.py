import streamlit as st
import requests
import math
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("POLYGON_API_KEY")

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

    # Use last 12 months to find low-high
    prices = [{"date": datetime.utcfromtimestamp(candle["t"] / 1000), "low": candle["l"], "high": candle["h"], "close": candle["c"]} for candle in data]
    recent = prices[-12:]

    # Find local low first, then local high after it
    local_low = min(recent[:-4], key=lambda x: x["low"])  # Allow 3+ months buffer
    low_index = recent.index(local_low)
    local_high = max(recent[low_index + 1:], key=lambda x: x["high"])
    high_index = recent.index(local_high)

    if high_index <= low_index:
        return False  # No valid move

    # Calculate 0.618 retracement
    retrace_price = log_fib_0618(local_low["low"], local_high["high"])

    # Get most recent month (April 2025)
    latest = recent[-1]
    if abs(latest["close"] - retrace_price) / retrace_price <= 0.35:
        return {
            "ticker": ticker,
            "low": local_low["low"],
            "high": local_high["high"],
            "retraced_close": latest["close"],
            "expected_0618": retrace_price,
            "month": latest["date"].strftime("%b %Y")
        }

    return False

# User controls
max_tickers = st.slider("How many tickers to scan", 50, 500, 100, 50)

if st.button("Scan Now"):
    st.write("🔍 Scanning... This may take a few minutes.")
    tickers = get_tickers(limit=max_tickers)
    results = []

    progress = st.progress(0)
    for i, ticker in enumerate(tickers):
        match = scan_ticker(ticker)
        if match:
            results.append(match)
        progress.progress((i + 1) / len(tickers))

    st.success(f"✅ Scan complete. Found {len(results)} matches.")
    st.write("### 📈 Matching Tickers:")
    for r in results:
        st.write(f"**{r['ticker']}** | Month: {r['month']} | 0.618: ${r['expected_0618']} | Close: ${r['retraced_close']}")

