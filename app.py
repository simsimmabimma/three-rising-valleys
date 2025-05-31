import streamlit as st
import yfinance as yf
import pandas as pd
import re

st.set_page_config(page_title="Three Rising Valleys Screener", layout="wide")
st.title("📈 Three Rising Valleys Screener (Monthly)")

@st.cache_data
def get_all_usa_tickers():
    url = "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed-symbols.csv"
    df = pd.read_csv(url)
    tickers = df["Symbol"].dropna().astype(str).tolist()
    pattern = re.compile(r'^[A-Z0-9\.\-]+$')
    return [t for t in tickers if pattern.match(t)]

@st.cache_data
def fetch_monthly_data(ticker):
    df = yf.download(ticker, period="5y", interval="1mo", progress=False)
    return df[['Open', 'High', 'Low', 'Close']]

def is_three_rising_valleys(df, min_gap=0.5):
    lows = df['Low']
    valleys = []
    for i in range(2, len(lows)-2):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            valleys.append((i, lows[i]))
    if len(valleys) < 3:
        return False
    v1, v2, v3 = valleys[-3:]
    return (
        v1[1] < v2[1] * (1 - min_gap / 100) and
        v2[1] < v3[1] * (1 - min_gap / 100)
    )

if "all_tickers" not in st.session_state:
    st.session_state.all_tickers = get_all_usa_tickers()

if st.button("Run Full Screener (Scan all tickers)"):
    results = []
    with st.spinner(f"Scanning {len(st.session_state.all_tickers[:1000])} tickers..."):
        for ticker in st.session_state.all_tickers[:1000]:
            try:
                df = fetch_monthly_data(ticker)
                if is_three_rising_valleys(df):
                    results.append(ticker)
            except Exception:
                pass
    st.success(f"✅ Found {len(results)} matches.")
    st.write(results)

