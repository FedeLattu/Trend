# config.py

stop_loss = 1
volatility_stop_multiplier = 8 #put high number to not have stop loss triggered

# Trailing profit stop settings
enable_trailing_take_profit = False 
take_profit_trigger = 0.10 # 10% unrealized gain before trailing stop activates
take_profit_fraction = 0.5  # lock in 50% of profits once above trigger

asset_config = {
    
    "SPY": {"initial_capital": 10000},
    #"VHYG.L": {"initial_capital": 10000},
    #"IGLN.L": {"initial_capital": 10000},
    #"EWG": {"initial_capital": 10000},
    #"EWP": {"initial_capital": 10000},
    #"H4ZX.DE": {"initial_capital": 10000},

}

start_date = "2000-01-01"
end_date = "2025-10-04"

halflife = 100
signal_smooth_halflife = 100
slope_window = 50
require_positive_signal = True
