import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Function to fetch monthly stock data
def get_monthly_data(ticker, period="2y"):
    stock = yf.Ticker(ticker)
    # Fetch historical data
    data = stock.history(period=period)
    # Resample to monthly data, taking the last price of each month
    monthly_data = data['Close'].resample('M').last()
    # Create a DataFrame
    df = pd.DataFrame({
        'Date': monthly_data.index,
        'Close': monthly_data.values,
        'Low': data['Low'].resample('M').min(),
        'High': data['High'].resample('M').max()
    })
    return df

# Function to detect Three Rising Valleys pattern
def detect_three_rising_valleys(df, lookback=12):
    # Look for valleys (local minima) in the Low prices
    valleys = []
    for i in range(1, len(df)-1):
        if df['Low'].iloc[i] < df['Low'].iloc[i-1] and df['Low'].iloc[i] < df['Low'].iloc[i+1]:
            valleys.append((df['Date'].iloc[i], df['Low'].iloc[i], i))
    
    # Check for three rising valleys
    patterns = []
    for i in range(len(valleys)-2):
        valley1, valley2, valley3 = valleys[i], valleys[i+1], valleys[i+2]
        date1, low1, idx1 = valley1
        date2, low2, idx2 = valley2
        date3, low3, idx3 = valley3
        
        # Check if lows are rising
        if low1 < low2 < low3:
            # Check if the peaks between valleys are not significantly declining
            peak1 = df['High'].iloc[idx1:idx2].max()
            peak2 = df['High'].iloc[idx2:idx3].max()
            # Ensure peaks are not significantly lower (e.g., within 10% of previous peak)
            if peak2 >= peak1 * 0.9:
                patterns.append({
                    'Ticker': ticker,
                    'Valley1': {'Date': date1, 'Low': low1},
                    'Valley2': {'Date': date2, 'Low': low2},
                    'Valley3': {'Date': date3, 'Low': low3},
                    'Peak1': peak1,
                    'Peak2': peak2
                })
    
    return patterns

# Main function to scan stocks
def scan_stocks(tickers):
    print("Scanning stocks for Three Rising Valleys pattern...")
    for ticker in tickers:
        try:
            # Fetch monthly data
            df = get_monthly_data(ticker)
            if len(df) < 6:  # Ensure enough data points
                continue
            
            # Detect patterns
            patterns = detect_three_rising_valleys(df)
            
            # Print results
            for pattern in patterns:
                print(f"\nPotential Three Rising Valleys pattern found for {ticker}:")
                print(f"Valley 1: {pattern['Valley1']['Date'].date()} at ${pattern['Valley1']['Low']:.2f}")
                print(f"Valley 2: {pattern['Valley2']['Date'].date()} at ${pattern['Valley2']['Low']:.2f}")
                print(f"Valley 3: {pattern['Valley3']['Date'].date()} at ${pattern['Valley3']['Low']:.2f}")
                print(f"Peak 1: ${pattern['Peak1']:.2f}")
                print(f"Peak 2: ${pattern['Peak2']:.2f}")
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

# Example usage
if __name__ == "__main__":
    # List of stock tickers to scan (you can expand this list)
    tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 
        'JPM', 'BAC', 'WFC', 'GS', 'C',
        'XOM', 'CVX', 'SPY', 'QQQ'
    ]
    
    # Scan stocks
    scan_stocks(tickers)
