# summary.py

import pandas as pd

def summarize_trades(trades, asset_config):
    if not trades:
        print("No trades executed.")
        return

    # Convert trade list to DataFrame
    summary_df = pd.DataFrame(trades)

    # --- Portfolio-Level Summary ---
    portfolio_start_value = sum(config["initial_capital"] for config in asset_config.values())
    portfolio_final_value = summary_df.groupby("symbol")["equity"].last().sum()
    portfolio_pnl = portfolio_final_value - portfolio_start_value
    portfolio_return_pct = (portfolio_final_value / portfolio_start_value - 1) * 100

    # --- Per-Symbol Summary ---
    for symbol in asset_config:
        df = summary_df[summary_df["symbol"] == symbol]
        if df.empty:
            continue

        print(f"\n>> {symbol} SUMMARY")

        total_trades = len(df)
        total_pnl = df["pnl"].sum()
        final_equity = df["equity"].iloc[-1]

        # Compute expected return
        win_trades = df[df["pct_return"] > 0]
        loss_trades = df[df["pct_return"] <= 0]

        p_win = len(win_trades) / total_trades
        p_loss = 1 - p_win

        avg_win_return = win_trades["pct_return"].mean() if not win_trades.empty else 0
        avg_loss_return = loss_trades["pct_return"].mean() if not loss_trades.empty else 0

        expected_return = p_win * avg_win_return + p_loss * avg_loss_return

        print(f"Trades: {total_trades} | Total PnL: ${total_pnl:.2f} | Final Equity: ${final_equity:.2f}")
        print(f"Expected Return per Trade: {expected_return:.2f}% | Win Rate: {p_win * 100:.2f}%")

        # Print each trade with return
        for _, t in df.iterrows():
            highest_profit = t.get('highest_profit_pct', None)
            trailing_stop = t.get('trailing_stop_price', None)

            highest_profit_str = f"{highest_profit:.2f}%" if highest_profit is not None else "N/A"
            trailing_stop_str = f"${trailing_stop:.2f}" if trailing_stop is not None else "N/A"

            print(
                f"{t['entry_time'].date()} → {t['exit_time'].date()} | "
                f"Entry: ${t['entry_price']:.2f} | Exit: ${t['exit_price']:.2f} | "
                f"PnL: ${t['pnl']:.2f} | Return: {t['pct_return']:.2f}% | "
                f"Stop Loss %: {t['stop_loss_pct']:.2f}% | "
                f"Max Profit Seen: {highest_profit_str} | "
                f"Trailing Stop Used: {trailing_stop_str} | "
                f"Reason: {t['exit_reason']}"
            )

    # --- Portfolio Summary ---
    print("\n=== PORTFOLIO SUMMARY ===")
    print(f"Starting Value: ${portfolio_start_value:.2f}")
    print(f"Final Value:   ${portfolio_final_value:.2f}")
    print(f"Total PnL:     ${portfolio_pnl:.2f}")
    print(f"Return:        {portfolio_return_pct:.2f}%")

    # --- Daily Portfolio PnL ---
    summary_df['exit_date'] = pd.to_datetime(summary_df['exit_time']).dt.date
    daily_pnl = summary_df.groupby('exit_date')['pnl'].sum().reset_index()
    daily_pnl.columns = ['date', 'daily_pnl']

    # Return both for plotting or saving
    return summary_df, daily_pnl
