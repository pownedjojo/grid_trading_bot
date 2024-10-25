import logging
import numpy as np
from tabulate import tabulate

ANNUAL_RISK_FREE_RATE = 0.03  # annual risk free rate 3%

class TradingPerformanceAnalyzer:
    def __init__(self, config_manager, order_book):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.order_book = order_book
        self.initial_balance, self.base_currency, self.quote_currency, self.trading_fee = self._extract_config()
    
    def _extract_config(self):
        initial_balance = self.config_manager.get_initial_balance()
        base_currency = self.config_manager.get_base_currency()
        quote_currency = self.config_manager.get_quote_currency()
        trading_fee = self.config_manager.get_trading_fee()
        return initial_balance, base_currency, quote_currency, trading_fee
    
    def _calculate_roi(self, final_balance):
        roi = (final_balance - self.initial_balance) / self.initial_balance * 100
        return round(roi, 2)
    
    def _calculate_trading_gains(self):
        total_buy_cost = 0
        total_sell_revenue = 0
        buy_orders = self.order_book.get_all_buy_orders()
        sell_orders = self.order_book.get_all_sell_orders()

        for buy_order in buy_orders:
            trade_value = buy_order.quantity * buy_order.price
            buy_fee = trade_value * self.trading_fee
            total_buy_cost += trade_value + buy_fee

        for sell_order in sell_orders:
            trade_value = sell_order.quantity * sell_order.price
            sell_fee = trade_value * self.trading_fee
            total_sell_revenue += trade_value - sell_fee

        grid_trading_gains = total_sell_revenue - total_buy_cost
        return grid_trading_gains

    def _calculate_drawdown(self, data):
        peak = data['account_value'].expanding(min_periods=1).max()
        drawdown = (peak - data['account_value']) / peak * 100
        max_drawdown = drawdown.max()
        return max_drawdown

    def _calculate_runup(self, data):
        trough = data['account_value'].expanding(min_periods=1).min()
        runup = (data['account_value'] - trough) / trough * 100
        max_runup = runup.max()
        return max_runup

    def _calculate_time_in_profit_loss(self, data):
        time_in_profit = (data['account_value'] > self.initial_balance).mean() * 100
        time_in_loss = (data['account_value'] <= self.initial_balance).mean() * 100
        return time_in_profit, time_in_loss
    
    def _calculate_sharpe_ratio(self, data):
        returns = data['account_value'].pct_change(fill_method=None)
        excess_returns = returns - ANNUAL_RISK_FREE_RATE / 252 # Adjusted daily
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        return round(sharpe_ratio, 2)
    
    def _calculate_sortino_ratio(self, data):
        returns = data['account_value'].pct_change(fill_method=None)
        excess_returns = returns - ANNUAL_RISK_FREE_RATE / 252  # Adjusted daily
        downside_returns = excess_returns[excess_returns < 0]
        sortino_ratio = excess_returns.mean() / downside_returns.std() * np.sqrt(252)
        return round(sortino_ratio, 2)

    def _get_formatted_orders(self):
        orders = []
        buy_orders_with_grid = self.order_book.get_buy_orders_with_grid()
        sell_orders_with_grid = self.order_book.get_sell_orders_with_grid()

        for buy_order, grid_level in buy_orders_with_grid:
            orders.append(self._format_order(buy_order, grid_level))

        for sell_order, grid_level in sell_orders_with_grid:
            orders.append(self._format_order(sell_order, grid_level))
        
        orders.sort(key=lambda x: (x[3] is None, x[3]))  # x[3] is the timestamp, sort None to the end
        return orders
    
    def _format_order(self, order, grid_level):
        grid_level_price = grid_level.price if grid_level else "N/A"
        # Assuming order.price is the execution price and grid level price the expected price
        slippage = ((order.price - grid_level_price) / grid_level_price) * 100 if grid_level else "N/A"
        return [
            order.order_type.name,
            order.price, 
            order.quantity, 
            order.timestamp, 
            grid_level_price, 
            f"{slippage:.2f}%" if grid_level else "N/A"
        ]
    
    def _calculate_trade_counts(self):
        num_buy_trades = len(self.order_book.get_all_buy_orders())
        num_sell_trades = len(self.order_book.get_all_sell_orders())
        return num_buy_trades, num_sell_trades
    
    def _calculate_buy_and_hold_return(self, data, final_price):
        initial_price = data['close'].iloc[0]
        return ((final_price - initial_price) / initial_price) * 100

    def generate_performance_summary(self, data, balance, crypto_balance, final_crypto_price, total_fees):
        pair = f"{self.base_currency}/{self.quote_currency}"
        start_date = data.index[0]
        end_date = data.index[-1]
        duration = end_date - start_date
        final_balance = balance + crypto_balance * final_crypto_price
        roi = self._calculate_roi(final_balance)
        grid_trading_gains = self._calculate_trading_gains()
        max_drawdown = self._calculate_drawdown(data)
        max_runup = self._calculate_runup(data)
        time_in_profit, time_in_loss = self._calculate_time_in_profit_loss(data)
        sharpe_ratio = self._calculate_sharpe_ratio(data)
        sortino_ratio = self._calculate_sortino_ratio(data)
        buy_and_hold_return = self._calculate_buy_and_hold_return(data, final_crypto_price)
        num_buy_trades, num_sell_trades = self._calculate_trade_counts()
        
        performance_summary = {
            "Pair": pair,
            "Start Date": start_date,
            "End Date": end_date,
            "Duration": duration,
            "ROI": f"{roi:.2f}%",
            "Max Drawdown": f"{max_drawdown:.2f}%",
            "Max Runup": f"{max_runup:.2f}%",
            "Time in Profit %": f"{time_in_profit:.2f}%",
            "Time in Loss %": f"{time_in_loss:.2f}%",
            "Buy and Hold Return %": f"{buy_and_hold_return:.2f}%",
            "Grid Trading Gains": f"{grid_trading_gains:.2f}",
            "Total Fees": f"{total_fees:.2f}",
            "Final Balance": f"{final_balance:.2f}",
            "Number of Buy Trades": num_buy_trades,
            "Number of Sell Trades": num_sell_trades,
            "Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Sortino Ratio": f"{sortino_ratio:.2f}"
        }

        formatted_orders = self._get_formatted_orders()

        orders_table = tabulate(formatted_orders, headers=["Order Type", "Price", "Quantity", "Timestamp", "Grid Level", "Slippage"], tablefmt="pipe")
        self.logger.info("\nFormatted Orders:\n" + orders_table)

        summary_table = tabulate(performance_summary.items(), headers=["Metric", "Value"], tablefmt="grid")
        self.logger.info("\nPerformance Summary:\n" + summary_table)

        return performance_summary, formatted_orders