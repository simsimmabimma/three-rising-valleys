import streamlit as st
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("uK8VVf63Y1jBNNOmUKOnpp8BEUI8e4Gw")

BASE_URL = "https://api.polygon.io"

st.title("Test SOFI Monthly Data Fetch")

def get_monthly_data(ticker="SOFI"):
    to_date = datetime.today().strftime("%Y-%m-%d")
    from_date = (datetime.today() - timedelta(days=730)).strftime("%Y-%m-%d")  # 2 years ago
    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/month/{from_date}/{to_date}?adjusted=true&sort=asc&apiKey={API_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        st.error(f"API request failed with status {resp.status_code}: {resp.text}")
        return None
    json_data = resp.json()
    return json_data

st.write("Fetching monthly data for SOFI...")
data = get_monthly_data()

if data:
    st.write("Raw API response:")
    st.json(data)

    results = data.get("results", [])
    if not results:
        st.write("No monthly data found.")
    else:
        st.write(f"Found {len(results)} months of data:")
        for candle in results:
            dt = datetime.utcfromtimestamp(candle["t"] / 1000)
            st.write(f"{dt.strftime('%b %Y')}: Low={candle['l']}, High={candle['h']}, Close={candle['c']}")
else:
    st.write("Failed to fetch data.")
