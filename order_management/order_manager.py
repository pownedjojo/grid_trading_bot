import logging
from .order import Order, OrderType
from .grid_level import GridLevel, GridCycleState
from .transaction_validator import InsufficientBalanceError, GridLevelNotReadyError

class OrderManager:
    def __init__(self, config_manager, grid_manager, transaction_validator, fee_calculator):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.grid_manager = grid_manager
        self.validator = transaction_validator
        self.fee_calculator = fee_calculator
        self.grid_levels = {}
        self.total_trading_fees = 0
        self.trade_percentage = 0.1 # TODO: Make use of: self.config_manager.get_trade_percentage

    def initialize_grid_levels(self):
        grids, central_price = self.grid_manager.grids, self.grid_manager.central_price
        self.grid_levels = {price: GridLevel(price, GridCycleState.READY_TO_BUY if price <= central_price else GridCycleState.READY_TO_SELL) for price in grids}
    
    def execute_order(self, order_type: OrderType, current_price, previous_price, timestamp, balance, crypto_balance):
        grid_price = self.grid_manager.detect_grid_level_crossing(current_price, previous_price, sell=(order_type == OrderType.SELL))

        if grid_price is None:
            self.logger.info(f"No grid level crossed for {order_type}.")
            return balance, crypto_balance
        
        grid_level_crossed = self.grid_levels[grid_price]
        try:
            if order_type == OrderType.BUY:
                return self._process_buy_order(grid_level_crossed, current_price, timestamp, balance, crypto_balance)
            elif order_type == OrderType.SELL:
                return self._process_sell_order(grid_level_crossed, current_price, timestamp, balance, crypto_balance)
        except ValueError as e:
            self.logger.warning(f"Failed to place {order_type} order: {e}")
            return balance, crypto_balance
    
    def get_orders(self):
        buy_orders = [order for grid_level in self.grid_levels.values() for order in grid_level.buy_orders]
        sell_orders = [order for grid_level in self.grid_levels.values() for order in grid_level.sell_orders]
        return buy_orders, sell_orders
    
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
    
    def _process_buy_order(self, grid_level, current_price, timestamp, balance, crypto_balance):
        try:
            quantity = self.trade_percentage * balance / current_price
            self.validator.validate_buy_order(balance, quantity, current_price, grid_level)
            fee = self.fee_calculator.calculate_fee(quantity * current_price)
            balance -= quantity * current_price + fee
            crypto_balance += quantity
            self.total_trading_fees += fee
            self._place_order(grid_level, OrderType.BUY, current_price, quantity, timestamp)
            return balance, crypto_balance
        except (InsufficientBalanceError, GridLevelNotReadyError, ValueError) as e:
            self.logger.error(f"Error processing buy order: {e}")
            return balance, crypto_balance
        except Exception as e:
            self.logger.error(f"Unexpected error in _process_buy_order: {e}")
            return balance, crypto_balance
    
    def _process_sell_order(self, grid_level, current_price, timestamp, balance, crypto_balance):
        try:
            buy_grid_level = self.grid_manager.find_lowest_completed_buy_grid(self.grid_levels)
            buy_order = buy_grid_level.buy_orders[-1]
            quantity = buy_order.quantity
            self.validator.validate_sell_order(crypto_balance, quantity, grid_level)
            fee = self.fee_calculator.calculate_fee(quantity * current_price)
            balance += quantity * current_price - fee
            crypto_balance -= quantity
            self.total_trading_fees += fee
            self._place_order(grid_level, OrderType.SELL, current_price, quantity, timestamp)
            self._reset_grid_cycle(buy_grid_level)
            return balance, crypto_balance
        except (InsufficientBalanceError, GridLevelNotReadyError, ValueError) as e:
            self.logger.error(f"Error processing sell order: {e}")
            return balance, crypto_balance
        except Exception as e:
            self.logger.error(f"Unexpected error in _process_sell_order: {e}")
            return balance, crypto_balance
    
    def _place_order(self, grid_level, order_type, current_price, quantity, timestamp):
        order = Order(current_price, quantity, order_type, timestamp)
        if order_type == OrderType.BUY:
            grid_level.place_buy_order(order)
        else:
            grid_level.place_sell_order(order)
        self.logger.info(f"{order_type} order placed at {current_price}.")

    def _reset_grid_cycle(self, buy_grid_level):
        buy_grid_level.reset_buy_level_cycle()
        self.logger.info(f"Buy Grid level at price {buy_grid_level.price} is reset and ready for the next buy/sell cycle.")