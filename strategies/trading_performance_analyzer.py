import numpy as np
from tabulate import tabulate
from order_management.order import OrderType

class TradingPerformanceAnalyzer:
    def __init__(self, config_manager, order_manager):
        self.config_manager = config_manager
        self.order_manager = order_manager
        self.initial_balance, self.base_currency, self.quote_currency, self.trading_fee = self.extract_config()
    
    def extract_config(self):
        initial_balance = self.config_manager.get_initial_balance()
        base_currency = self.config_manager.get_base_currency()
        quote_currency = self.config_manager.get_quote_currency()
        trading_fee = self.config_manager.get_trading_fee()
        return initial_balance, base_currency, quote_currency, trading_fee
    
    def calculate_roi(self, final_balance):
        roi = (final_balance - self.initial_balance) / self.initial_balance * 100
        return round(roi, 2)
    
    def calculate_trading_gains(self):
        total_buy_cost = 0
        total_sell_revenue = 0
        
        for grid_level in self.order_manager.grid_levels.values():
            for buy_order in grid_level.buy_orders:
                trade_value = buy_order.quantity * buy_order.price
                buy_fee = trade_value * self.trading_fee
                total_buy_cost += trade_value + buy_fee

            for sell_order in grid_level.sell_orders:
                trade_value = sell_order.quantity * sell_order.price
                sell_fee = trade_value * self.trading_fee
                total_sell_revenue += trade_value - sell_fee
        
        grid_trading_gains = total_sell_revenue - total_buy_cost
        return grid_trading_gains

    def calculate_drawdown(self, data):
        peak = data['account_value'].expanding(min_periods=1).max()
        drawdown = (peak - data['account_value']) / peak * 100
        max_drawdown = drawdown.max()
        return max_drawdown

    def calculate_runup(self, data):
        trough = data['account_value'].expanding(min_periods=1).min()
        runup = (data['account_value'] - trough) / trough * 100
        max_runup = runup.max()
        return max_runup

    def calculate_time_in_profit_loss(self, data):
        time_in_profit = (data['account_value'] > self.initial_balance).mean() * 100
        time_in_loss = (data['account_value'] <= self.initial_balance).mean() * 100
        return time_in_profit, time_in_loss
    
    def calculate_sharpe_ratio(self, data):
        risk_free_rate = 0.02  # annual risk free rate 2%
        returns = data['account_value'].pct_change().dropna()
        excess_returns = returns - risk_free_rate / 252 # Adjusted daily
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        return round(sharpe_ratio, 2)
    
    def calculate_sortino_ratio(self, data):
        risk_free_rate = 0.02  # annual risk free rate 2%
        returns = data['account_value'].pct_change().dropna()
        excess_returns = returns - risk_free_rate / 252  # Adjusted daily
        downside_returns = excess_returns[excess_returns < 0]
        sortino_ratio = excess_returns.mean() / downside_returns.std() * np.sqrt(252)
        return round(sortino_ratio, 2)

    def display_orders(self):
        orders = []
        for grid_level in self.order_manager.grid_levels.values():
            for buy_order in grid_level.buy_orders:
                orders.append(self.format_order(buy_order, grid_level))
            for sell_order in grid_level.sell_orders:
                orders.append(self.format_order(sell_order, grid_level))

        orders.sort(key=lambda x: x[3])  # x[3] is the timestamp
        print(tabulate(orders, headers=["Order Type", "Price", "Quantity", "Timestamp", "Grid Level"], tablefmt="pipe"))

    def format_order(self, order, grid_level):
        order_type = "BUY" if order.order_type == OrderType.BUY else "SELL"
        return [order_type, order.price, order.quantity, order.timestamp, grid_level.price]
    
    def calculate_trade_counts(self):
        num_buy_trades = sum(len(grid_level.buy_orders) for grid_level in self.order_manager.grid_levels.values())
        num_sell_trades = sum(len(grid_level.sell_orders) for grid_level in self.order_manager.grid_levels.values())
        return num_buy_trades, num_sell_trades
    
    def calculate_buy_and_hold_return(self, data, final_price):
        initial_price = data['close'].iloc[0]
        return ((final_price - initial_price) / initial_price) * 100

    def generate_performance_summary(self, data, balance, crypto_balance, final_crypto_price):
        self.display_orders()
        pair = f"{self.base_currency}/{self.quote_currency}"
        start_date = data.index[0]
        end_date = data.index[-1]
        duration = end_date - start_date
        final_balance = balance + crypto_balance * final_crypto_price
        roi = self.calculate_roi(final_balance)
        grid_trading_gains = self.calculate_trading_gains()
        max_drawdown = self.calculate_drawdown(data)
        max_runup = self.calculate_runup(data)
        time_in_profit, time_in_loss = self.calculate_time_in_profit_loss(data)
        sharpe_ratio = self.calculate_sharpe_ratio(data)
        sortino_ratio = self.calculate_sortino_ratio(data)
        buy_and_hold_return = self.calculate_buy_and_hold_return(data, final_crypto_price)
        num_buy_trades, num_sell_trades = self.calculate_trade_counts()
        
        performance_summary = [
            ["Pair", pair],
            ["Start Date", start_date],
            ["End Date", end_date],
            ["Duration", duration],
            ["ROI", f"{roi:.2f}%"],
            ["Max Drawdown", f"{max_drawdown:.2f}%"],
            ["Max Runup", f"{max_runup:.2f}%"],
            ["Time in Profit %", f"{time_in_profit:.2f}%"],
            ["Time in Loss %", f"{time_in_loss:.2f}%"],
            ["Buy and Hold Return %", f"{buy_and_hold_return:.2f}%"],
            ["Grid Trading Gains", f"{grid_trading_gains:.2f}"],
            ["Final Balance", f"{final_balance:.2f}"],
            ["Number of Buy Trades", num_buy_trades],
            ["Number of Sell Trades", num_sell_trades],
            ["Sharpe Ratio", f"{sharpe_ratio:.2f}"],
            ["Sortino Ratio", f"{sortino_ratio:.2f}"]
        ]
        print(tabulate(performance_summary, headers=["Metric", "Value"], tablefmt="grid"))