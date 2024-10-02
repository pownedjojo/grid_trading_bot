import logging, itertools
import numpy as np
from .plotter import Plotter
from .base import TradingStrategy
from .grid_manager import GridManager
from order_management.order_manager import OrderManager
from order_management.order import Order, OrderType
from .trading_performance_analyzer import TradingPerformanceAnalyzer

class GridTradingStrategy(TradingStrategy):
    def __init__(self, config_manager, data_manager, grid_manager, order_manager, balance_tracker, trading_performance_analyzer, plotter):
        super().__init__(config_manager)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.grid_manager = grid_manager
        self.order_manager = order_manager
        self.balance_tracker = balance_tracker
        self.trading_performance_analyzer = trading_performance_analyzer
        self.plotter = plotter
        pair, timeframe, start_date, end_date = self._extract_config()
        self._initialize_strategy(pair, timeframe, start_date, end_date)
    
    def _extract_config(self):
        pair = f"{self.config_manager.get_base_currency()}/{self.config_manager.get_quote_currency()}"
        timeframe = self.config_manager.get_timeframe()
        start_date = self.config_manager.get_start_date()
        end_date = self.config_manager.get_end_date()
        return pair, timeframe, start_date, end_date

    def _initialize_strategy(self, pair, timeframe, start_date, end_date):
        self.load_data(self.data_manager.fetch_ohlcv(pair, timeframe, start_date, end_date))
        self.order_manager.initialize_grid_levels()

    def simulate(self):
        self.logger.info("Start trading simulation")
        self.data['account_value'] = np.nan
        self.close_prices = self.data['close'].values
        timestamps = self.data.index

        for (current_price, previous_price), current_timestamp in zip(itertools.pairwise(self.close_prices), timestamps[1:]):
            if self.check_take_profit_stop_loss(current_price):
                self.logger.info("Take profit or stop loss triggered, ending simulation")
                break
            self._execute_orders(current_price, previous_price, current_timestamp)
            self.data['account_value'].loc[current_timestamp] = self.balance_tracker.balance + self.balance_tracker.crypto_balance * current_price

    def generate_performance_report(self):
        final_price = self.close_prices[-1]
        self.trading_performance_analyzer.generate_performance_summary(
            self.data, 
            self.balance_tracker.balance, 
            self.balance_tracker.crypto_balance, 
            final_price
        )

    def plot_results(self):
        self.plotter.plot_results(self.data)
    
    def _execute_orders(self, current_price, previous_price, current_timestamp):
        self.order_manager.execute_order(OrderType.BUY, current_price, previous_price, current_timestamp)
        self.order_manager.execute_order(OrderType.SELL, current_price, previous_price, current_timestamp)