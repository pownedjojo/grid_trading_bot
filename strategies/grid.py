import logging
import pandas as pd
from .plotter import Plotter
from .base import TradingStrategy
from .grid_manager import GridManager
from order_management.order_manager import OrderManager
from .performance_metrics import PerformanceMetrics

class GridTradingStrategy(TradingStrategy):
    def __init__(self, config_manager, data_manager, grid_manager, order_manager, performance_metrics, plotter):
        super().__init__(config_manager)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.grid_manager = grid_manager
        self.order_manager = order_manager
        self.performance_metrics = performance_metrics
        self.plotter = plotter
        pair, timeframe, start_date, end_date = self.extract_config()
        self.initialize_strategy(pair, timeframe, start_date, end_date)
    
    def extract_config(self):
        pair_config = self.config_manager.get_base_currency()
        pair = f"{self.config_manager.get_base_currency()}/{self.config_manager.get_quote_currency()}"
        timeframe = self.config_manager.get_timeframe()
        start_date = self.config_manager.get_start_date()
        end_date = self.config_manager.get_end_date()
        return pair, timeframe, start_date, end_date

    def initialize_strategy(self, pair, timeframe, start_date, end_date):
        self.load_data(self.data_manager.fetch_ohlcv(pair, timeframe, start_date, end_date))
        self.grids = self.grid_manager.calculate_grids()
        self.central_price = self.grid_manager.get_central_price()
        self.order_manager.initialize_grid_orders(self.grids)
        self.grid_orders = self.order_manager.grid_orders

    def simulate(self):
        self.logger.info("Starting simulation")
        initial_price = self.data['close'].iloc[0]
        self.start_crypto_balance = self.crypto_balance

        for i in range(1, len(self.data)):
            current_price = self.data['close'].iloc[i]
            previous_price = self.data['close'].iloc[i - 1]
            current_timestamp = self.data.index[i]
            self.logger.debug(f"Current price: {current_price}, Previous price: {previous_price}")

            if self.check_take_profit_stop_loss(current_price):
                self.logger.info("Take profit or stop loss triggered, ending simulation")
                break

            self.execute_orders(current_price, current_timestamp)

        final_price = self.data['close'].iloc[-1]
        self.performance_metrics.calculate_gains(initial_price, final_price, self.start_crypto_balance, self.balance, self.crypto_balance)
        self.data['account_value'] = self.balance + self.crypto_balance * self.data['close']

    def execute_orders(self, current_price, current_timestamp):
        buy_grids = [price for price in sorted(self.grid_orders.keys()) if price <= self.central_price]
        sell_grids = [price for price in sorted(self.grid_orders.keys()) if price > self.central_price]

        for buy_grid_price in buy_grids:
            if self.order_manager.can_place_buy_order(buy_grid_price, current_price):
                self.buy(buy_grid_price, current_timestamp)

        for sell_grid_price in sell_grids:
            if self.order_manager.can_place_sell_order(sell_grid_price, current_price):
                buy_order = self.order_manager.find_buy_order_for_sale(sell_grid_price)
                if buy_order is not None:
                    self.sell(sell_grid_price, buy_order, current_timestamp)
                    self.logger.info(f"Sell order placed at {sell_grid_price} for timestamp {current_timestamp}")
                else:
                    self.logger.info(f"No corresponding buy order found for sell order at price {sell_grid_price}")

    def buy(self, price, timestamp):
        self.balance, self.crypto_balance = self.order_manager.place_buy_order(price, timestamp, self.balance, self.crypto_balance)
        self.logger.info(f"Placing buy order at {price} on {timestamp}. Updated balance: {self.balance}, crypto balance: {self.crypto_balance}")

    def sell(self, price, buy_order, timestamp):
        self.balance, self.crypto_balance = self.order_manager.place_sell_order(price, buy_order, timestamp, self.balance, self.crypto_balance)
        self.logger.info(f"Placing sell order at {price} on {timestamp}. Updated balance: {self.balance}, crypto balance: {self.crypto_balance}")

    def calculate_performance_metrics(self):
        final_balance = self.balance + self.crypto_balance * self.data['close'].iloc[-1]
        roi = self.performance_metrics.calculate_roi(final_balance)
        max_drawdown = round(self.calculate_drawdown(), 2)
        max_runup = round(self.calculate_runup(), 2)
        time_in_profit = round(self.calculate_time_in_profit_loss()[0], 2)
        time_in_loss = round(self.calculate_time_in_profit_loss()[1], 2)
        sharpe_ratio = self.calculate_sharpe_ratio()
        sortino_ratio = self.calculate_sortino_ratio()
        num_buy_trades = len(self.order_manager.buy_orders)
        num_sell_trades = len(self.order_manager.sell_orders)
        performance_summary = self.performance_metrics.generate_performance_summary(self.data, self.crypto_balance, self.data['close'].iloc[-1], roi, max_drawdown, max_runup, time_in_profit, time_in_loss, num_buy_trades, num_sell_trades, sharpe_ratio, sortino_ratio)
        return performance_summary

    def plot_results(self):
        self.plotter.plot_results(self.data, self.grids, self.order_manager.buy_orders, self.order_manager.sell_orders)