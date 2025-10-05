# data.py
import yfinance as yf
import pandas as pd

def download_price_data(symbol, start_date, end_date):
    data = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True)
    return data[["Close", "Open"]].dropna()
