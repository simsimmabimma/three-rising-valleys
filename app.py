import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math

st.title("📉 Monthly 0.618 Retracement Scanner")

# Load tickers from file or use fixed list
@st.cache_data
def load_tickers():
    try:
        with open("tickers.txt") as f:
            return [line.strip().upper() for line in f if line.strip()]
    except FileNotFoundError:
        # fallback list
        return ["AAPL", "MSFT", "TSLA", "GOOG", "SOFI", "AMZN", "NVDA", "META", "NFLX"]

tickers = load_tickers()

def meets_criteria(ticker):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info

        market_cap = info.get("marketCap", 0)
        avg_volume = info.get("averageVolume", 0)
        
        hist = tk.history(period="4y", interval="1d")
        if hist.empty:
            return False
        
        first_date = hist.index[0]
        if first_date > datetime.now() - timedelta(days=3*365):
            return False
        
        if avg_volume < 1_000_000 or market_cap < 1_000_000_000:
            return False
        
        return True
    except Exception as e:
        return False

def log_fib_0618(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    log_retracement = log_high - 0.618 * log_diff
    return round(math.exp(log_retracement), 2)

def check_retracement(ticker):
    try:
        tk = yf.Ticker(ticker)
        data = tk.history(period="2y", interval="1mo")
        if data.empty or len(data) < 6:
            return False
        
        lows = data['Low'].tolist()
        highs = data['High'].tolist()
        dates = data.index.tolist()
        
        swing_low = min(lows)
        swing_low_idx = lows.index(swing_low)
        
        if swing_low_idx == len(lows) - 1:
            return False
        
        swing_high = max(highs[swing_low_idx+1:])
        swing_high_idx = highs[swing_low_idx+1:].index(swing_high) + swing_low_idx + 1
        
        retrace_price = log_fib_0618(swing_low, swing_high)
        
        recent_lows = lows[-3:]
        retraced = any(low <= retrace_price for low in recent_lows)
        
        if retraced:
            retraced_month_idx = len(lows) - 3 + [low <= retrace_price for low in recent_lows].index(True)
            retraced_month = dates[retraced_month_idx].strftime("%b %Y")
            
            return {
                "Ticker": ticker,
                "Swing Low": swing_low,
                "Swing High": swing_high,
                "0.618 Retracement": retrace_price,
                "Retraced Month": retraced_month,
                "Retraced Low": recent_lows[retraced_month_idx - (len(lows)-3)]
            }
        return False
    except:
        return False

if st.button("Run Scan"):
    st.write(f"Scanning {len(tickers)} tickers. This may take several minutes...")
    
    results = []
    for i, ticker in enumerate(tickers):
        st.write(f"Checking {ticker} ({i+1}/{len(tickers)})")
        if meets_criteria(ticker):
            res = check_retracement(ticker)
            if res:
                results.append(res)
    
    if results:
        df = pd.DataFrame(results)
        st.write("Tickers meeting retracement pattern:")
        st.dataframe(df)
    else:
        st.write("No tickers met retracement pattern.")
else:
    st.write("Click the 'Run Scan' button to start scanning.")
