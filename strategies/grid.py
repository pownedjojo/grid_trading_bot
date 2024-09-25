import logging, itertools
import pandas as pd
from .plotter import Plotter
from .base import TradingStrategy
from .grid_manager import GridManager
from order_management.order_manager import OrderManager
from order_management.order import Order, OrderType
from .trading_performance_analyzer import TradingPerformanceAnalyzer

class GridTradingStrategy(TradingStrategy):
    def __init__(self, config_manager, data_manager, grid_manager, order_manager, trading_performance_analyzer, plotter):
        super().__init__(config_manager)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.grid_manager = grid_manager
        self.order_manager = order_manager
        self.trading_performance_analyzer = trading_performance_analyzer
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
        self.order_manager.initialize_grid_levels(self.grids, self.central_price)
        self.start_crypto_balance = self.crypto_balance

    def simulate(self):
        self.logger.info("Start trading simulation")
        self.extract_price_and_timestamps()
    
        for (current_price, previous_price), current_timestamp in zip(itertools.pairwise(self.close_prices), self.timestamps[1:]):
            if self.check_take_profit_stop_loss(current_price):
                self.logger.info("Take profit or stop loss triggered, ending simulation")
                break
            self.execute_orders(current_price, previous_price, current_timestamp)
        self.finalize_simulation()
    
    def extract_price_and_timestamps(self):
        self.close_prices = self.data['close'].values
        self.timestamps = self.data.index
        self.initial_price = self.close_prices[0]
    
    def execute_orders(self, current_price, previous_price, current_timestamp):
        self.handle_order_execution(current_price, previous_price, current_timestamp, OrderType.BUY)
        self.handle_order_execution(current_price, previous_price, current_timestamp, OrderType.SELL)
    
    def handle_order_execution(self, current_price, previous_price, timestamp, order_type: OrderType):
        try:
            self.balance, self.crypto_balance = self.order_manager.execute_order(order_type, current_price, previous_price, timestamp, self.balance, self.crypto_balance)
        except ValueError as e:
            self.logger.error(f"Error placing {order_type} order: {e}")

    def finalize_simulation(self):
        self.final_price = self.close_prices[-1]
        self.data['account_value'] = self.balance + self.crypto_balance * self.close_prices

    def generate_performance_report(self):
        self.trading_performance_analyzer.generate_performance_summary(self.data, self.balance, self.crypto_balance, self.final_price)

    def plot_results(self):
        self.plotter.plot_results(self.data, self.grids)