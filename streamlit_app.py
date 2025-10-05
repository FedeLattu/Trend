import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

from config import (
    start_date, end_date, halflife,
    signal_smooth_halflife, slope_window,
    require_positive_signal, volatility_stop_multiplier,
    take_profit_trigger, take_profit_fraction, enable_trailing_take_profit
)
from data import download_price_data
from indicators import calculate_ew_returns, calculate_ew_volatility, calculate_signal, rolling_slope
from strategy import run_strategy
from summary import summarize_trades

# --- Auth ---

st.set_page_config(page_title="Trading Strategy", layout="wide")
st.title("Dashboard")
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    password = st.text_input("Enter password:", type="password")
    if password == st.secrets["app_password"]:
        st.session_state["authenticated"] = True
    else:
        st.stop()

# --- Parameters ---
st.sidebar.header("Strategy Parameters")

# --- User Input Asset ---
st.sidebar.header("Asset Input")
ticker = st.sidebar.text_input("Enter Asset Ticker as shown in yahoo finance")
initial_capital = st.sidebar.number_input("Enter Initial Capital", min_value=1000, step=100, value=10000)

start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime(start_date))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime(end_date))

halflife = st.sidebar.slider("Halflife for EWMA", 10, 200, int(halflife))
signal_smooth_halflife = st.sidebar.slider("Signal Smooth Halflife", 10, 200, int(signal_smooth_halflife))
slope_window = st.sidebar.slider("Slope Window", 10, 100, int(slope_window))
volatility_stop_multiplier = st.sidebar.slider("Volatility Stop Multiplier", 1.0, 10.0, float(volatility_stop_multiplier), step=0.1)
require_positive_signal = st.sidebar.checkbox("Require Positive Signal", value=require_positive_signal)

# --- Trailing Take Profit ---
enable_trailing_take_profit = st.sidebar.checkbox("Enable Trailing Take Profit", enable_trailing_take_profit)
take_profit_trigger = st.sidebar.number_input("Take Profit Trigger (as decimal)", 0.01, 1.0, take_profit_trigger)
take_profit_fraction = st.sidebar.number_input("Take Profit Fraction (as decimal)", 0.1, 1.0, take_profit_fraction)

if not ticker:
    st.warning("Please enter a ticker symbol.")
    st.stop()

# --- Data Load ---
st.write("## Strategy Results")
data = download_price_data(ticker, start_date, end_date)

if data is None or data.empty:
    st.error(f"No data found for {ticker}")
    st.stop()

price_close = data["Close"].squeeze()
price_open = data["Open"].squeeze()

returns = price_close / price_close.shift(1)
returns = returns.apply(lambda x: np.nan if x <= 0 else np.log(x))

ewma_returns = calculate_ew_returns(returns, halflife)
ewma_volatility = calculate_ew_volatility(returns, halflife)
signal = 100 * calculate_signal(returns, ewma_volatility, halflife)
smoothed_signal = signal.ewm(halflife=signal_smooth_halflife).mean()
slope_series = rolling_slope(smoothed_signal, slope_window)

stop_loss_series = volatility_stop_multiplier * ewma_volatility
warmup = max(halflife, signal_smooth_halflife, slope_window)

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios': [2, 1.5, 1]})

trades = run_strategy(
    symbol=ticker,
    price_series=price_open.iloc[warmup:],
    signal_series=smoothed_signal.iloc[warmup:],
    slope_series=slope_series.iloc[warmup:],
    stop_loss_series=stop_loss_series.iloc[warmup:],
    returns=returns,
    initial_capital=initial_capital,
    require_positive_signal=require_positive_signal,
    ax1=ax1, ax2=ax2, ax3=ax3,
    enable_trailing_take_profit=enable_trailing_take_profit,
    take_profit_trigger=take_profit_trigger,
    take_profit_fraction=take_profit_fraction
)

for ax in [ax1, ax2, ax3]:
    ax.legend()
    ax.grid(True)

ax1.set_title("Price with Trades")
ax2.set_title("Smoothed Signal")
ax3.set_title("Slope")
ax3.set_xlabel("Date")

st.pyplot(fig)

summary_df, daily_pnl_df = summarize_trades(trades, {ticker: {"initial_capital": initial_capital}})

# --- Portfolio Summary in Streamlit ---
if not summary_df.empty:
    portfolio_start_value = initial_capital
    portfolio_final_value = summary_df.groupby("symbol")["equity"].last().sum()
    portfolio_pnl = portfolio_final_value - portfolio_start_value
    portfolio_return_pct = (portfolio_final_value / portfolio_start_value - 1) * 100

    total_trades = len(summary_df)
    total_pnl = summary_df["pnl"].sum()
    final_equity = summary_df["equity"].iloc[-1]

    win_trades = summary_df[summary_df["pct_return"] > 0]
    p_win = len(win_trades) / total_trades if total_trades > 0 else 0
    expected_return = (
        (p_win * win_trades["pct_return"].mean() if not win_trades.empty else 0) +
        ((1 - p_win) * summary_df[summary_df["pct_return"] <= 0]["pct_return"].mean()
         if not summary_df[summary_df["pct_return"] <= 0].empty else 0)
    )

    st.subheader("Performance Summary")
    st.write(
        f"**Trades:** {total_trades} | "
        f"**Total PnL:** {total_pnl:,.2f} | "
        f"**Final Equity:** {final_equity:,.2f}"
    )
    st.write(
        f"**Expected Return per Trade:** {expected_return:.2f}% | "
        f"**Win Rate:** {p_win * 100:.2f}%"
    )

    st.write(f"**Starting Value:** {portfolio_start_value:,.2f}")
    st.write(f"**Final Value:**   {portfolio_final_value:,.2f}")
    st.write(f"**Total PnL:**     {portfolio_pnl:,.2f}")
    st.write(f"**Return:**        {portfolio_return_pct:.2f}%")


# --- Clean and Show Summary Table ---
st.subheader("Trade Summary Table")

# Prepare and format summary table
summary_df["Entry Date"] = pd.to_datetime(summary_df["entry_time"]).dt.date
summary_df["Exit Date"] = pd.to_datetime(summary_df["exit_time"]).dt.date

columns_to_show = [
    "Entry Date", "Exit Date",
    "entry_price", "exit_price",
    "pnl", "pct_return",
    "stop_loss_pct", "highest_profit_pct",
    "trailing_stop_price", "exit_reason"
]

column_renames = {
    "entry_price": "Entry Price",
    "exit_price": "Exit Price",
    "pnl": "PnL",
    "pct_return": "Return %",
    "stop_loss_pct": "Stop Loss %",
    "highest_profit_pct": "Max Profit Seen %",
    "trailing_stop_price": "Trailing Stop Used",
    "exit_reason": "Exit eason"
}

summary_df_filtered = summary_df[columns_to_show].rename(columns=column_renames)

st.dataframe(summary_df_filtered, width=1800, height=800)

# --- Download ---
csv = summary_df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, "trade_summary.csv", "text/csv")


