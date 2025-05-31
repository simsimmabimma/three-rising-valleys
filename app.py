import streamlit as st
import yfinance as yf
import math
from datetime import datetime, timedelta
import pandas as pd

st.title("Monthly 0.618 Retracement Scanner (Log Scale) - Multi Ticker")

def log_fib_0618(low, high):
    log_low = math.log(low)
    log_high = math.log(high)
    log_diff = log_high - log_low
    log_retracement = log_high - 0.618 * log_diff
    return round(math.exp(log_retracement), 2)

def passes_filters(tk):
    info = tk.info
    try:
        # Check listing age ≥ 3 years
        ipo_date = info.get('ipoDate')
        if ipo_date is None:
            return False
        ipo_dt = datetime.strptime(ipo_date, "%Y-%m-%d")
        if (datetime.now() - ipo_dt).days < 365 * 3:
            return False

        # Market Cap ≥ 1B
        market_cap = info.get('marketCap', 0)
        if market_cap < 1_000_000_000:
            return False

        # Average volume ≥ 1M (3 months)
        hist = tk.history(period="3mo", interval="1d")
        if hist.empty:
            return False
        avg_volume = hist['Volume'].mean()
        if avg_volume < 1_000_000:
            return False

        return True
    except Exception:
        return False

def check_retracement(ticker):
    tk = yf.Ticker(ticker)
    data = tk.history(period="2y", interval="1mo")

    if data.empty or len(data) < 6:
        return None

    lows = data['Low'].tolist()
    highs = data['High'].tolist()
    dates = data.index.tolist()

    swing_low = min(lows)
    swing_low_idx = lows.index(swing_low)

    highs_after_low = highs[swing_low_idx + 1:]
    if not highs_after_low:
        return None
    swing_high = max(highs_after_low)
    swing_high_idx = highs_after_low.index(swing_high) + swing_low_idx + 1

    retrace_price = log_fib_0618(swing_low, swing_high)

    last_3_lows = lows[-3:]
    last_3_dates = dates[-3:]

    for d, low in zip(last_3_dates, last_3_lows):
        if low <= retrace_price:
            return {
                "Ticker": ticker,
                "Swing Low": swing_low,
                "Swing Low Date": dates[swing_low_idx].strftime("%Y-%m"),
                "Swing High": swing_high,
                "Swing High Date": dates[swing_high_idx].strftime("%Y-%m"),
                "Fib 0.618 Retracement": retrace_price,
                "Retracement Dip Date": d.strftime("%Y-%m"),
                "Retracement Low": low,
            }
    return None

# Main scanning button
if st.button("Scan S&P 500 tickers"):

    st.info("Fetching tickers and filtering by listing age, volume, and market cap...")
    sp500_tickers = yf.Tickers(' '.join(yf.Tickers().tickers_sp500))

    filtered_tickers = []
    for ticker in yf.Tickers().tickers_sp500:
        tk = yf.Ticker(ticker)
        if passes_filters(tk):
            filtered_tickers.append(ticker)

    st.write(f"Tickers after filtering: {len(filtered_tickers)}")

    results = []
    progress_bar = st.progress(0)
    total = len(filtered_tickers)

    for i, ticker in enumerate(filtered_tickers):
        res = check_retracement(ticker)
        if res:
            results.append(res)
        progress_bar.progress((i + 1) / total)

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found {len(results)} tickers with retracement dip.")
        st.dataframe(df)
    else:
        st.warning("No tickers found with retracement dip.")

