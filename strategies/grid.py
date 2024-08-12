import pandas as pd
import logging
from .grid_manager import GridManager
from .order_manager import OrderManager
from .performance_metrics import PerformanceMetrics
from .plotter import Plotter
from .base import TradingStrategy

class GridTradingStrategy(TradingStrategy):
    def __init__(self, config):
        super().__init__(config)
        grid_params = config['grid']
        self.base_currency = config['pair']['base_currency']
        self.quote_currency = config['pair']['quote_currency']
        self.trigger_price = grid_params.get('trigger_price')
        self.trade_percentage = grid_params.get('trade_percentage', 0.1)  # Default to 10%
        self.grid_manager = GridManager(grid_params['bottom_range'], grid_params['top_range'], grid_params['num_grids'], grid_params['spacing_type'], grid_params.get('percentage_spacing', 0.05))
        self.order_manager = OrderManager(self.trade_percentage, config['exchange']['trading_fee'])
        self.performance_metrics = PerformanceMetrics()
        self.plotter = Plotter()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.grids = self.grid_manager.calculate_grids()
        self.trading_active = self.trigger_price is None
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

            self.activate_trading(current_price)

            if self.trading_active:
                if self.check_take_profit_stop_loss(current_price):
                    self.logger.info("Take profit or stop loss triggered, ending simulation")
                    break

                self.execute_orders(current_price, current_timestamp)

        final_price = self.data['close'].iloc[-1]
        self.performance_metrics.calculate_gains(initial_price, final_price, self.start_crypto_balance, self.initial_balance, self.balance, self.crypto_balance)
        self.data['account_value'] = self.balance + self.crypto_balance * self.data['close']

    ## TODO: handle trigger_price null - if trigger_price null => trigger_price should be market price when simulation starts
    def activate_trading(self, current_price):
        if not self.trading_active and self.trigger_price is not None and current_price >= self.trigger_price:
            self.trading_active = True
            self.logger.info(f"Grid Trading activated at {current_price}")

    def execute_orders(self, current_price, current_timestamp):
        if self.trigger_price is not None:
            buy_grids = [price for price in sorted(self.grid_orders.keys()) if price <= self.trigger_price]
            sell_grids = [price for price in sorted(self.grid_orders.keys()) if price > self.trigger_price]

            for price in buy_grids:
                self.logger.info(f"Checking buy conditions at {current_timestamp}: current_price={current_price}, price={price}, trigger_price={self.trigger_price}, buy_quantity={self.grid_orders[price]['buy_quantity']}")
                if current_price <= price and self.order_manager.can_place_buy_order(price):
                    self.buy(price, current_timestamp)

            for price in sell_grids:
                self.logger.info(f"Checking sell conditions at {current_timestamp}: current_price={current_price}, price={price}, trigger_price={self.trigger_price}, buy_quantity={self.grid_orders[price]['buy_quantity']}, sell_quantity={self.grid_orders[price]['sell_quantity']}")
                if self.order_manager.can_place_sell_order(price, current_price):
                    buy_order = self.order_manager.find_buy_order_for_sale(price)
                    if buy_order is not None:
                        self.sell(price, buy_order, current_timestamp)
                        self.logger.info(f"Sell order placed at {price} for timestamp {current_timestamp}")
                    else:
                        self.logger.info(f"No corresponding buy order found for sell order at price {price}")

    def buy(self, price, timestamp):
        self.balance, self.crypto_balance = self.order_manager.place_buy_order(price, timestamp, self.balance, self.crypto_balance)
        self.logger.info(f"Placing buy order at {price} on {timestamp}. Quantity: {self.order_manager.grid_orders[price]['buy_quantity']}, Updated balance: {self.balance}, crypto balance: {self.crypto_balance}")

    def sell(self, price, buy_order, timestamp):
        self.balance, self.crypto_balance = self.order_manager.place_sell_order(price, buy_order, timestamp, self.balance, self.crypto_balance)
        self.logger.info(f"Placing sell order at {price} on {timestamp}. Updated balance: {self.balance}, crypto balance: {self.crypto_balance}")

    def calculate_performance_metrics(self):
        final_balance = self.balance + self.crypto_balance * self.data['close'].iloc[-1]
        final_balance, roi = self.performance_metrics.calculate_roi(self.initial_balance, final_balance)
        max_drawdown = round(self.calculate_drawdown(), 2)
        max_runup = round(self.calculate_runup(), 2)
        time_in_profit = round(self.calculate_time_in_profit_loss()[0], 2)
        time_in_loss = round(self.calculate_time_in_profit_loss()[1], 2)
        sharpe_ratio = self.calculate_sharpe_ratio()
        sortino_ratio = self.calculate_sortino_ratio()
        num_buy_trades = len(self.order_manager.buy_orders)
        num_sell_trades = len(self.order_manager.sell_orders)

        performance_summary = self.performance_metrics.generate_performance_summary(
            self.data, self.initial_balance, self.crypto_balance, self.data['close'].iloc[-1], roi, max_drawdown, max_runup, time_in_profit, time_in_loss, num_buy_trades, num_sell_trades, sharpe_ratio, sortino_ratio, self.base_currency, self.quote_currency
        )
        return performance_summary

    def plot_results(self):
        self.plotter.plot_results(self.data, self.grids, self.order_manager.buy_orders, self.order_manager.sell_orders, self.trigger_price)