# strategy.py
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def run_strategy(
    symbol,
    price_series,
    signal_series,
    slope_series,
    stop_loss_series,
    returns,
    initial_capital,
    require_positive_signal,
    ax1, ax2, ax3,
    enable_trailing_take_profit=True,
    take_profit_trigger=0.10,      # new param (fraction, e.g. 0.10 = 10%)
    take_profit_fraction=0.50      # new param (fraction, e.g. 0.50 = 50%)
):
    # Initialize variables
    position = None
    current_equity = initial_capital
    cumulative_pct_return = 1.0
    auto_trades = []

    for i in range(1, len(slope_series) - 1):
        prev_slope = slope_series.iloc[i - 1]
        curr_slope = slope_series.iloc[i]
        date = slope_series.index[i]

        if date not in price_series or date not in signal_series or date not in stop_loss_series:
            continue

        # --- BUY ---
        buy_signal = prev_slope < 0 and curr_slope >= 0
        if require_positive_signal:
            buy_signal = buy_signal and signal_series.loc[date] > 0

        if buy_signal and position is None:
            next_date = price_series.index[i + 1]
            entry_price = price_series.loc[next_date]
            volatility_stop_pct = stop_loss_series.loc[date]
            stop_loss_price = entry_price * (1 - volatility_stop_pct)

            position = {
                'entry_time': next_date,
                'entry_price': entry_price,
                'shares': current_equity / entry_price,
                'stop_loss_price': stop_loss_price,
                'stop_loss_pct': volatility_stop_pct * 100,  # Save as percent
                'highest_profit_pct': 0.0,
                'trailing_stop_price': None
            }

            ax1.axvline(next_date, color='green', linestyle=':', alpha=0.5)
            ax3.plot(next_date, curr_slope, 'go', markersize=8,
                     label=f"{symbol} Buy" if len(auto_trades) == 0 else "")

        # --- SELL ---
        if position is not None:
            shares = position['shares']
            entry_price = position['entry_price']
            stop_loss_price = position['stop_loss_price']
            trailing_stop_price = position['trailing_stop_price']
            highest_profit_pct = position['highest_profit_pct']

            current_price = price_series.loc[date]
            unrealized_pct = (current_price - entry_price) / entry_price * 100

            # --- Update trailing stop if enabled ---
            if enable_trailing_take_profit:
                if unrealized_pct >= take_profit_trigger * 100:
                    highest_profit_pct = max(highest_profit_pct, unrealized_pct)
                    new_trailing_stop = entry_price * (
                        1 + take_profit_fraction * highest_profit_pct / 100
                    )
                    if trailing_stop_price is None:
                        trailing_stop_price = new_trailing_stop
                    else:
                        trailing_stop_price = max(trailing_stop_price, new_trailing_stop)

                    position['highest_profit_pct'] = highest_profit_pct
                    position['trailing_stop_price'] = trailing_stop_price

            # --- Check exit conditions ---
            stop_loss_triggered = current_price <= stop_loss_price
            trailing_stop_triggered = (
                enable_trailing_take_profit
                and trailing_stop_price is not None
                and current_price <= trailing_stop_price
            )
            slope_sell = prev_slope > 0 and curr_slope <= 0

            sell_signal = stop_loss_triggered or trailing_stop_triggered or slope_sell

            if sell_signal:
                next_date = price_series.index[i + 1]
                exit_price = price_series.loc[next_date]

                pct_return = (exit_price - entry_price) / entry_price
                absolute_pnl = shares * (exit_price - entry_price)

                cumulative_pct_return *= (1 + pct_return)
                current_equity *= (1 + pct_return)

                if stop_loss_triggered:
                    trade_type = "Stop Loss Sell"
                elif trailing_stop_triggered:
                    trade_type = "Trailing Stop Sell"
                else:
                    trade_type = "Slope Sell"

                trade_color = (
                    'red' if stop_loss_triggered
                    else 'purple' if trailing_stop_triggered
                    else 'black'
                )

                auto_trades.append({
                    'symbol': symbol,
                    'entry_time': position['entry_time'],
                    'exit_time': next_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'shares': shares,
                    'pnl': absolute_pnl,
                    'pct_return': pct_return * 100,
                    'cumulative_pct_return': (cumulative_pct_return - 1) * 100,
                    'equity': current_equity,
                    'exit_reason': trade_type,
                    'stop_loss_pct': position.get('stop_loss_pct', None),
                    'highest_profit_pct': highest_profit_pct,
                    'trailing_stop_price': trailing_stop_price
                })

                ax1.axvline(next_date, color=trade_color, linestyle=':', alpha=0.5)
                ax3.plot(next_date, curr_slope, 'ro', markersize=8,
                         label=f"{symbol} Sell" if len(auto_trades) == 1 else "")
                position = None

    # --- Forced sell at end of backtest ---
    if position is not None:
        final_date = price_series.index[-1]
        final_price = price_series.iloc[-1]
        shares = position['shares']
        entry_price = position['entry_price']

        pct_return = (final_price - entry_price) / entry_price
        absolute_pnl = shares * (final_price - entry_price)

        cumulative_pct_return *= (1 + pct_return)
        current_equity *= (1 + pct_return)

        auto_trades.append({
            'symbol': symbol,
            'entry_time': position['entry_time'],
            'exit_time': final_date,
            'entry_price': entry_price,
            'exit_price': final_price,
            'shares': shares,
            'pnl': absolute_pnl,
            'pct_return': pct_return * 100,
            'cumulative_pct_return': (cumulative_pct_return - 1) * 100,
            'equity': current_equity,
            'exit_reason': "Forced Sell",
            'stop_loss_pct': position.get('stop_loss_pct', None),
            'highest_profit_pct': position.get('highest_profit_pct', None),
            'trailing_stop_price': position.get('trailing_stop_price', None)
        })

        ax1.axvline(final_date, color='orange', linestyle=':', alpha=0.5)

    # --- Plot ---
    ax1.plot(price_series.index, price_series, label=f"{symbol} Price Series")
    ax2.plot(signal_series.index, signal_series, label=f"{symbol} Smoothed Signal")
    ax3.plot(slope_series.index, slope_series, label=f"{symbol} Slope")

    # --- Highlight trades on cumulative return ---
    price_series_subset = price_series.copy()
    for trade in auto_trades:
        entry = trade["entry_time"]
        exit_ = trade["exit_time"]
        pnl = trade["pnl"]

        trade_slice = price_series_subset.loc[entry:exit_]
        color = '#66FF00' if pnl >= 0 else 'red'
        ax1.plot(trade_slice.index, trade_slice.values, color=color, linewidth=2)

    return auto_trades
