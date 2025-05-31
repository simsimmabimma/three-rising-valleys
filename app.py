import streamlit as st
import requests
import math
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("A_xj1Mwz42bTgVFi6Hz0gOEm4Olk9aDH")
BASE_URL = "https://api.polygon.io"

@st.cache_data(ttl=24*3600)  # Cache tickers for 24 hours
def get_all_usa_tickers():
    url = f"{BASE_URL}/v3/reference/tickers"
    params = {
        "market": "stocks",
        "active": "true",
        "limit": 1000,
        "apiKey": API_KEY,
        "locale": "US"
    }
    tickers = []
    cursor = None

    while True:
        if cursor:
            params["cursor"] = cursor
        response = requests.get(url, params=params)
        data = response.json()

        if "results" not in data:
            st.error(f"Error fetching tickers: {data.get('error', 'Unknown error')}")
            break

        tickers.extend([t["ticker"] for t in data["results"]])
        cursor = data.get("next_page_token", None)
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
        return Fal
