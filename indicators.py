# indicators.py
import numpy as np

def calculate_ew_volatility(returns, halflife):
    return returns.ewm(halflife=halflife).std()

def calculate_ew_returns(returns, halflife):
    return returns.ewm(halflife=halflife).mean()

def calculate_signal(returns, ewvol, halflife):
    rar = returns / ewvol
    return rar.ewm(halflife=halflife).mean()

def rolling_slope(series, window):
    def _slope(x):
        t = np.arange(len(x))
        slope, _ = np.polyfit(t, x, 1)
        return slope
    return series.rolling(window).apply(_slope, raw=True)
