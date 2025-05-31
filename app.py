import streamlit as st
import requests
import math
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("POLYGON_API_KEY")

BASE_URL = "https://api.polygon.io"

@st.cache_data(ttl=24*3600)  # Cache for 24 hours
def get_all_usa_tickers():
    url = f"{BASE_URL}/v3/reference/tickers"
    params = {
        "market": "stocks",
        "active": "true",
        "limit": 1000,  # max per page
        "apiKey": API_KEY,
    }
    tickers = []
    cursor = None
    while True:
        if cursor:
            params["cursor"] = cursor
        response = requests.get(url, params=params)
        data = response.json()
        if "results" not in data:
            break
        tickers.extend([t["ticker"] for t in data["results"] if t["market"] == "stocks" and t["locale"] == "US"])
        cursor = data.get("next_url", None)
        if not cursor:
            break
    return list(set(tickers))

@st.cache_data(ttl=12*3600)  # Cache monthly bars for 12 hours
def get_monthly_bars(ticker):
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/month/2000-01-01/2100-01-01"
    params = {"adjusted": "true", "sort": "asc", "limit": 1000, "apiKey": API_KEY}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if "results" not in data:
        return None
    bars = data["results"]
    return bars

def log_618_retracement(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    retrace_log = log_high - 0.618 * (log_high - log_low)
    return math.exp(retrace_log)

def check_pattern(ticker, bars):
    if not bars or len(bars) < 18:
        return False

    # Use last 18 months only
    bars = bars[-18:]

    lows = [b["l"] for b in bars]
    highs = [b["h"] for b in bars]

    swing_low = min(lows)
    swing_high = max(highs)
    retrace_price = log_618_retracement(swing_low, swing_high)

    # Check last 3 months lows <= retracement level
    last_3_lows = lows[-3:]
    return any(low <= retrace_price for low in last_3_lows)

def main():
    st.title("Monthly 3-Month 0.618 Retracement Scanner")

    with st.spinner("Fetching US tickers..."):
        tickers = get_all_usa_tickers()

    st.write(f"Total tickers fetched: {len(tickers)}")

    matched = []
    progress_bar = st.progress(0)
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        bars = get_monthly_bars(ticker)
        if check_pattern(ticker, bars):
            matched.append(ticker)
        progress_bar.progress((i + 1) / total)

    st.success(f"Found {len(matched)} matching stocks.")
    st.write(matched)

if __name__ == "__main__":
    main()
