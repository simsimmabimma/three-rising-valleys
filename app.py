import streamlit as st
import yfinance as yf
import pandas as pd
import math
import random
from datetime import datetime

st.set_page_config(page_title="Monthly 0.618 Retracement Scanner (USA Stocks Batch)", layout="wide")

st.title("📉 Monthly 0.618 Retracement Scanner for USA Stocks (Batch Scan)")

# URLs of public ticker lists
NASDAQ_URL = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
NYSE_URL = "https://raw.githubusercontent.com/datasets/nyse-listings/master/data/nyse-listed-symbols.csv"
AMEX_URL = "https://raw.githubusercontent.com/datasets/amex-listings/master/data/amex-listed-symbols.csv"

@st.cache_data(ttl=24*3600)
def load_all_usa_tickers():
    nasdaq = pd.read_csv(NASDAQ_URL)
    nyse = pd.read_csv(NYSE_URL)
    amex = pd.read_csv(AMEX_URL)

    # Extract symbols and upper-case them
    nasdaq_syms = nasdaq['Symbol'].str.upper().tolist()
    nyse_syms = nyse['ACT Symbol'].str.upper().tolist() if 'ACT Symbol' in nyse.columns else nyse['Symbol'].str.upper().tolist()
    amex_syms = amex['ACT Symbol'].str.upper().tolist() if 'ACT Symbol' in amex.columns else amex['Symbol'].str.upper().tolist()

    all_symbols = set(nasdaq_syms + nyse_syms + amex_syms)
    return list(all_symbols)

@st.cache_data(ttl=24*3600)
def get_ticker_info(ticker):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        return {
            "marketCap": info.get("marketCap", 0),
            "averageVolume": info.get("averageVolume", 0),
            "startDate": info.get("startDate", None),
            "regularMarketPrice": info.get("regularMarketPrice", None),
        }
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def get_monthly_data(ticker):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="3y", interval="1mo")
        hist = hist.reset_index()
        return hist
    except Exception:
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

    swing_low = hist['Low'].min()
    swing_low_date = hist.loc[hist['Low'].idxmin(),'Date']

    after_low = hist[hist['Date'] > swing_low_date]

    if after_low.empty:
        return False

    swing_high = after_low['High'].max()
    swing_high_date = after_low.loc[after_low['High'].idxmax(),'Date']

    if swing_high_date <= swing_low_date:
        return False

    retracement_price = log_fib_0618(swing_low, swing_high)

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

# Load all USA tickers from public CSVs
with st.spinner("Loading all USA tickers... This may take a moment."):
    all_tickers = load_all_usa_tickers()

# Initialize session state for shuffled tickers and index
if 'shuffled_tickers' not in st.session_state or 'current_index' not in st.session_state:
    st.session_state.shuffled_tickers = random.sample(all_tickers, len(all_tickers))
    st.session_state.current_index = 0

batch_size = 50
start_idx = st.session_state.current_index
end_idx = min(start_idx + batch_size, len(st.session_state.shuffled_tickers))
batch = st.session_state.shuffled_tickers[start_idx:end_idx]

# Update index for next batch or reshuffle when done
st.session_state.current_index = end_idx if end_idx < len(st.session_state.shuffled_tickers) else 0
if st.session_state.current_index == 0:
    st.session_state.shuffled_tickers = random.sample(all_tickers, len(all_tickers))

st.write(f"Scanning tickers {start_idx + 1} to {end_idx} of {len(all_tickers)}")

results = []

progress_bar = st.progress(0)
for i, ticker in enumerate(batch):
    info = get_ticker_info(ticker)
    if not info:
        continue

    market_cap = info.get("marketCap", 0)
    avg_vol = info.get("averageVolume", 0)
    start_date = info.get("startDate", None)

    if start_date:
        try:
            ipo_year = datetime.fromtimestamp(start_date).year
        except Exception:
            ipo_year = None
    else:
        ipo_year = None

    # Filters: Listed 3+ years, Market cap >1B, Avg volume >1M
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

st.write("Reload the app to scan the next batch of tickers.")

