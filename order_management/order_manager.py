import logging
from .order import Order, OrderType
from .grid_level import GridLevel, GridCycleState

class OrderManager:
    def __init__(self, config_manager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.trading_fee = self.config_manager.get_trading_fee()
        self.trade_percentage = 0.1 ## TODO: trade_percentage based on num_grids instead ? Default to 10%
        self.grid_levels = {}
        self.sorted_buy_grids = []
        self.sorted_sell_grids = []
        self.total_trading_fees = 0

    def initialize_grid_levels(self, grids, central_price):
        self.grid_levels = {price: GridLevel(price, GridCycleState.READY_TO_BUY if price <= central_price else GridCycleState.READY_TO_SELL) for price in grids}
        self.sorted_buy_grids = [price for price in sorted(grids) if price <= central_price]
        self.sorted_sell_grids = [price for price in sorted(grids) if price > central_price]
    
    def detect_grid_level_crossing(self, current_price, previous_price, sell=False):
        grid_list = self.sorted_sell_grids if sell else self.sorted_buy_grids
        for grid_price in grid_list:
            if (sell and previous_price < grid_price <= current_price) or (not sell and previous_price > grid_price >= current_price):
                return self.grid_levels[grid_price]
        return None

    def execute_order(self, order_type: OrderType, current_price, previous_price, timestamp, balance, crypto_balance):
        grid_level_crossed = self.detect_grid_level_crossing(current_price, previous_price, sell=(order_type == OrderType.SELL))

        if grid_level_crossed is None:
            self.logger.info(f"No grid level crossed for {order_type}.")
            return balance, crypto_balance

        try:
            if order_type == OrderType.BUY:
                return self._process_buy_order(grid_level_crossed, current_price, timestamp, balance, crypto_balance)
            elif order_type == OrderType.SELL:
                return self._process_sell_order(grid_level_crossed, current_price, timestamp, balance, crypto_balance)
        except ValueError as e:
            self.logger.warning(f"Failed to place {order_type} order: {e}")
            return balance, crypto_balance
    
    def _process_buy_order(self, grid_level, current_price, timestamp, balance, crypto_balance):
        if not grid_level.can_place_buy_order():
            raise ValueError(f"Cannot place buy order at grid level {grid_level.price} - state: {grid_level.cycle_state}")
        try:
            quantity = self.trade_percentage * balance / current_price
            balance, crypto_balance = self._place_order(grid_level, OrderType.BUY, current_price, quantity, timestamp, balance, crypto_balance)
        except ValueError as e:
            self.logger.error(f"Error placing buy order at {grid_level.price}: {e}")
            return balance, crypto_balance
        return balance, crypto_balance
    
    def _process_sell_order(self, grid_level, current_price, timestamp, balance, crypto_balance):
        try:
            buy_grid_level = self.find_lowest_completed_buy_order_grid_level()
            if not buy_grid_level or not buy_grid_level.buy_orders:
                raise ValueError(f"No completed buy order found for grid level {grid_level.price}")
            
            buy_order = buy_grid_level.buy_orders[-1]
            quantity = buy_order.quantity
            self.check_sufficient_crypto(crypto_balance, quantity, grid_level.price)
            balance, crypto_balance = self._place_order(grid_level, OrderType.SELL, current_price, quantity, timestamp, balance, crypto_balance)
            self.reset_grid_cycle(buy_grid_level)
        except ValueError as ve:
            self.logger.error(f"ValueError while processing sell order at grid level {grid_level.price}: {ve}")
        except Exception as e:
            self.logger.error(f"Unexpected error occurred while processing sell order at grid level {grid_level.price}: {e}")
        return balance, crypto_balance
    
    def _place_order(self, grid_level, order_type, current_price, quantity, timestamp, balance, crypto_balance):
        order = Order(current_price, quantity, order_type, timestamp)
        try:
            if order_type == OrderType.BUY:
                grid_level.place_buy_order(order)
            else:
                grid_level.place_sell_order(order)

            trade_value = quantity * current_price
            trade_fee = trade_value * self.trading_fee
            self.total_trading_fees += trade_fee

            if order_type == OrderType.SELL:
                balance += trade_value - trade_fee
                crypto_balance -= quantity
            else:
                balance -= trade_value + trade_fee
                crypto_balance += quantity

            self.logger.info(f"{order_type} order placed at {current_price}. Updated balance: {balance}, crypto balance: {crypto_balance}")
            return balance, crypto_balance
        except ValueError as e:
            self.logger.error(f"Failed to place {order_type} order: {e}")
            raise
    
    def find_lowest_completed_buy_order_grid_level(self):
        for grid_level_price in self.sorted_buy_grids:
            grid_level = self.grid_levels.get(grid_level_price)
            if grid_level and grid_level.can_place_sell_order():
                return grid_level
        raise ValueError("No grid level found with a completed buy order ready for a sell.")

    def check_sufficient_crypto(self, crypto_balance, quantity, grid_price):
        if crypto_balance < quantity:
            raise ValueError(f"Insufficient crypto balance to place sell order at {grid_price}")

    def reset_grid_cycle(self, buy_grid_level):
        buy_grid_level.reset_buy_level_cycle()
        self.logger.info(f"Buy Grid level at price {buy_grid_level.price} is reset and ready for the next buy/sell cycle.")
    
    def get_orders(self):
        buy_orders = [order for grid_level in self.grid_levels.values() for order in grid_level.buy_orders]
        sell_orders = [order for grid_level in self.grid_levels.values() for order in grid_level.sell_orders]
        return buy_orders, sell_orders