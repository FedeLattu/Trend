# main.py
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf

from config import (
    asset_config, start_date, end_date, halflife,
    signal_smooth_halflife, slope_window,
    require_positive_signal, volatility_stop_multiplier,
    take_profit_trigger, take_profit_fraction, enable_trailing_take_profit
)

from data import download_price_data
from indicators import calculate_ew_returns, calculate_ew_volatility, calculate_signal, rolling_slope
from strategy import run_strategy
from summary import summarize_trades

# --- Download both Close and Open ---
price_data_close = pd.DataFrame()
price_data_open = pd.DataFrame()

for symbol in asset_config:
    data = download_price_data(symbol, start_date, end_date)
    price_data_close[symbol] = data["Close"]
    price_data_open[symbol] = data["Open"]

# --- Calculations based on CLOSE prices ---
returns = np.log(price_data_close / price_data_close.shift(1))
ewma_returns = calculate_ew_returns(returns, halflife)
ewma_volatility = calculate_ew_volatility(returns, halflife)
signal = 100 * calculate_signal(returns, ewma_volatility, halflife)
smoothed_signal = signal.ewm(halflife=signal_smooth_halflife).mean()
slope_data = pd.DataFrame({s: rolling_slope(smoothed_signal[s], slope_window) for s in asset_config})

# --- Volatility-Based Stop-Loss Thresholds ---
# This gives you a daily % stop-loss value per asset
stop_loss_series = {
    symbol: volatility_stop_multiplier * ewma_volatility[symbol] for symbol in asset_config
}

warmup = max(halflife, signal_smooth_halflife, slope_window)

# --- Set up plots ---
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1.5, 1]})

all_trades = []

# --- Run strategy with dynamic stop-loss ---
for symbol, config in asset_config.items():
    trades = run_strategy(
        symbol=symbol,
        price_series=price_data_open[symbol].iloc[warmup:],   # EXECUTION at OPEN
        signal_series=smoothed_signal[symbol].iloc[warmup:], # SIGNAL from CLOSE
        slope_series=slope_data[symbol].iloc[warmup:],
        stop_loss_series=stop_loss_series[symbol].iloc[warmup:],
        returns=returns[symbol],
        initial_capital=config["initial_capital"],
        require_positive_signal=require_positive_signal,
        ax1=ax1, ax2=ax2, ax3=ax3,
        enable_trailing_take_profit=enable_trailing_take_profit,
        take_profit_trigger=take_profit_trigger,        
        take_profit_fraction=take_profit_fraction
    )
    all_trades.extend(trades)

# --- Finalize plots ---
for ax in [ax1, ax2, ax3]:
    ax.legend()
    ax.grid(True)


ax2.axhline(0, color='black', linestyle='--', linewidth=1)
ax3.axhline(0, color='black', linestyle='--', linewidth=1)
ax1.set_title("Cumulative Returns (Close-based)")
ax2.set_title("Smoothed Signal (Close-based)")
ax3.set_title("Slope of Smoothed Signal")
ax3.set_xlabel("Date")

summary_df, daily_pnl_df = summarize_trades(all_trades, asset_config)
plt.tight_layout()
plt.show()
