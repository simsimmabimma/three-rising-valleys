import streamlit as st
import yfinance as yf
import pandas as pd
import math
import random
from datetime import datetime

st.set_page_config(page_title="Monthly 0.618 Retracement Scanner (Batch Randomized)", layout="wide")

st.title("📉 Monthly 0.618 Retracement Scanner with Randomized Batch Scanning")

@st.cache_data(ttl=24*3600)
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    return df['Symbol'].tolist()

@st.cache_data(ttl=24*3600)
def get_ticker_info(ticker):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        return {
            "marketCap": info.get("marketCap", 0),
            "averageVolume": info.get("averageVolume", 0),
            "startDate": info.get("startDate", None),  # Unix timestamp or None
            "regularMarketPrice": info.get("regularMarketPrice", None),
        }
    except Exception as e:
        return {}

@st.cache_data(ttl=3600)
def get_monthly_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="3y", interval="1mo")
        hist = hist.reset_index()
        return hist
    except Exception as e:
        return pd.DataFrame()

def log_fib_0618(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    log_retracement = log_high - 0.618 * log_diff
    return round(math.exp(log_retracement), 2)

def check_retracement_pattern(hist):
    if hist.shape[0] < 6:
        return False

    # Find swing low (lowest low in last 3 years)
    swing_low = hist['Low'].min()
    swing_low_date = hist.loc[hist['Low'].idxmin(),'Date']

    # Filter data after swing low
    after_low = hist[hist['Date'] > swing_low_date]

    if after_low.empty:
        return False

    swing_high = after_low['High'].max()
    swing_high_date = after_low.loc[after_low['High'].idxmax(),'Date']

    # We want swing high after swing low
    if swing_high_date <= swing_low_date:
        return False

    # Calculate 0.618 retracement price on log scale
    retracement_price = log_fib_0618(swing_low, swing_high)

    # Check last 3 months if price dipped to or below retracement_price
    last_3m = hist[hist['Date'] > (hist['Date'].max() - pd.DateOffset(months=3))]
    dips_below_0618 = any(last_3m['Low'] <= retracement_price)

    if dips_below_0618:
        return {
            "swing_low": swing_low,
            "swing_low_date": swing_low_date.strftime("%Y-%m"),
            "swing_high": swing_high,
            "swing_high_date": swing_high_date.strftime("%Y-%m"),
            "retracement_price": retracement_price,
        }
    else:
        return False

# Load S&P 500 tickers
with st.spinner("Loading S&P 500 tickers..."):
    sp500_tickers = get_sp500_tickers()

# Initialize session state for shuffled tickers and index
if 'shuffled_tickers' not in st.session_state or 'current_index' not in st.session_state:
    st.session_state.shuffled_tickers = random.sample(sp500_tickers, len(sp500_tickers))
    st.session_state.current_index = 0

batch_size = 50

start_idx = st.session_state.current_index
end_idx = start_idx + batch_size
if end_idx > len(st.session_state.shuffled_tickers):
    end_idx = len(st.session_state.shuffled_tickers)

batch = st.session_state.shuffled_tickers[start_idx:end_idx]

st.session_state.current_index = end_idx if end_idx < len(st.session_state.shuffled_tickers) else 0
if st.session_state.current_index == 0:
    st.session_state.shuffled_tickers = random.sample(sp500_tickers, len(sp500_tickers))  # reshuffle after full cycle

st.write(f"Scanning tickers {start_idx + 1} to {end_idx} of {len(sp500_tickers)}")

results = []

progress_bar = st.progress(0)
for i, ticker in enumerate(batch):
    # Get ticker info and filter by criteria
    info = get_ticker_info(ticker)
    if not info:
        continue
    market_cap = info.get("marketCap", 0)
    avg_vol = info.get("averageVolume", 0)
    start_date = info.get("startDate", None)
    if start_date:
        try:
            ipo_year = datetime.fromtimestamp(start_date).year
        except:
            ipo_year = None
    else:
        ipo_year = None

    # Must be listed for at least 3 years
    if ipo_year is None or ipo_year > datetime.now().year - 3:
        continue
    if market_cap < 1e9:
        continue
    if avg_vol < 1_000_000:
        continue

    hist = get_monthly_data(ticker)
    if hist.empty:
        continue

    pattern = check_retracement_pattern(hist)
    if pattern:
        results.append({
            "Ticker": ticker,
            "Swing Low": pattern["swing_low"],
            "Swing Low Date": pattern["swing_low_date"],
            "Swing High": pattern["swing_high"],
            "Swing High Date": pattern["swing_high_date"],
            "Retracement Price (0.618 log)": pattern["retracement_price"],
        })

    progress_bar.progress((i+1)/len(batch))

progress_bar.empty()

if results:
    st.success(f"Found {len(results)} ticker(s) with 0.618 retracement dip in last 3 months!")
    st.dataframe(pd.DataFrame(results))
else:
    st.info("No tickers met the retracement criteria in this batch.")

st.write("Run the app again to scan the next batch of tickers.")


