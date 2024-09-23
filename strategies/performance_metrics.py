import pandas as pd

class PerformanceMetrics:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.initial_balance, self.base_currency, self.quote_currency = self.extract_config()
        self.appreciation_gains = 0
        self.grid_trading_gains = 0
    
    def extract_config(self):
        initial_balance = self.config_manager.get_initial_balance()
        base_currency = self.config_manager.get_base_currency()
        quote_currency = self.config_manager.get_quote_currency()
        return initial_balance, base_currency, quote_currency

    def calculate_gains(self, initial_price, final_price, start_crypto_balance, balance, crypto_balance):
        total_initial_crypto_value = self.initial_balance / initial_price
        self.appreciation_gains = (final_price - initial_price) * total_initial_crypto_value
        self.grid_trading_gains = (balance + crypto_balance * final_price) - self.initial_balance - self.appreciation_gains
        return self.appreciation_gains, self.grid_trading_gains

    def calculate_roi(self, final_balance):
        roi = (final_balance - self.initial_balance) / self.initial_balance * 100
        return round(roi, 2)
    
    def generate_performance_summary(self, data, final_balance, final_price, roi, max_drawdown, max_runup, time_in_profit, time_in_loss, num_buy_trades, num_sell_trades, sharpe_ratio, sortino_ratio):
        pair = f"{self.base_currency}/{self.quote_currency}"
        start_date = data.index[0]
        end_date = data.index[-1]
        duration = end_date - start_date
        buy_and_hold_return = ((final_price - data['close'].iloc[0]) / data['close'].iloc[0]) * 100
        
        performance_summary = {
            'Pair': pair,
            'Start Date': start_date,
            'End Date': end_date,
            'Duration': duration,
            'ROI': f"{roi:.2f}%",
            'Max Drawdown': f"{max_drawdown:.2f}%",
            'Max Runup': f"{max_runup:.2f}%",
            'Time in Profit %': f"{time_in_profit:.2f}%",
            'Time in Loss %': f"{time_in_loss:.2f}%",
            'Buy and Hold Return %': f"{buy_and_hold_return:.2f}%",
            'Appreciation Gains': f"{self.appreciation_gains:.2f}",
            'Grid Trading Gains': f"{self.grid_trading_gains:.2f}",
            'Final Balance': f"{final_balance:.2f}",
            'Number of Buy Trades': num_buy_trades,
            'Number of Sell Trades': num_sell_trades,
            'Sharpe Ratio': f"{sharpe_ratio:.2f}",
            'Sortino Ratio': f"{sortino_ratio:.2f}"
        }
        
        performance_df = pd.DataFrame.from_dict(performance_summary, orient='index', columns=['Value'])
        print(performance_df)
        return performance_summary