import logging
from .order import Order, OrderType
from validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError, GridLevelNotReadyError

class OrderManager:
    def __init__(self, config_manager, grid_manager, transaction_validator, balance_tracker, order_book):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.grid_manager = grid_manager
        self.transaction_validator = transaction_validator
        self.balance_tracker = balance_tracker
        self.order_book = order_book
        self.trade_percentage = self.config_manager.get_trade_percentage()

    def execute_order(self, order_type: OrderType, current_price, previous_price, timestamp):
        grid_price = self.grid_manager.detect_grid_level_crossing(current_price, previous_price, sell=(order_type == OrderType.SELL))

        if grid_price is None:
            self.logger.info(f"No grid level crossed for {order_type}.")
            return
        
        grid_level_crossed = self.grid_manager.get_grid_level(grid_price)
        if order_type == OrderType.BUY:
            self._process_buy_order(grid_level_crossed, current_price, timestamp)
        elif order_type == OrderType.SELL:
            self._process_sell_order(grid_level_crossed, current_price, timestamp)
    
    def execute_take_profit_or_stop_loss_order(self, current_price, timestamp, take_profit_order: bool=False, stop_loss_order: bool=False):
        if take_profit_order or stop_loss_order:
            order = Order(current_price, self.balance_tracker.crypto_balance, OrderType.SELL, timestamp)
            self.order_book.add_order(order)
            self.balance_tracker.sell_all(current_price)
            event = "Take profit" if take_profit_order else "Stop loss"
            self.logger.info(f"{event} triggered at {current_price}")
    
    def _process_buy_order(self, grid_level, current_price, timestamp):
        try:
            quantity = self.trade_percentage * self.balance_tracker.balance / current_price
            self.transaction_validator.validate_buy_order(self.balance_tracker.balance, quantity, current_price, grid_level)
            self._place_order(grid_level, OrderType.BUY, current_price, quantity, timestamp)
            self.balance_tracker.update_after_buy(quantity, current_price)
        except (InsufficientBalanceError, GridLevelNotReadyError, InsufficientCryptoBalanceError) as e:
            self.logger.info(f"Cannot process buy order: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while processing buy order: {e}")
    
    def _process_sell_order(self, grid_level, current_price, timestamp):
        buy_grid_level = self.grid_manager.find_lowest_completed_buy_grid()

        if buy_grid_level is None:
            self.logger.info(f"No grid level found with a completed buy order.")
            return

        try:
            buy_order = buy_grid_level.buy_orders[-1]
            quantity = buy_order.quantity
            self.transaction_validator.validate_sell_order(self.balance_tracker.crypto_balance, quantity, grid_level)
            self._place_order(grid_level, OrderType.SELL, current_price, quantity, timestamp)
            self.balance_tracker.update_after_sell(quantity, current_price)
            self._reset_grid_cycle(buy_grid_level)
        except (InsufficientBalanceError, GridLevelNotReadyError, InsufficientCryptoBalanceError) as e:
            self.logger.info(f"Cannot process sell order: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while processing sell order: {e}")
    
    def _place_order(self, grid_level, order_type, current_price, quantity, timestamp):
        order = Order(current_price, quantity, order_type, timestamp)
        if order_type == OrderType.BUY:
            if grid_level.can_place_buy_order():
                grid_level.place_buy_order(order)
            else:
                raise GridLevelNotReadyError(f"Grid level {grid_level.price} is not ready for a buy order, current state: {grid_level.cycle_state}")
        else:
            if grid_level.can_place_sell_order():
                grid_level.place_sell_order(order)
            else:
                raise GridLevelNotReadyError(f"Grid level {grid_level.price} is not ready for a sell order, current state: {grid_level.cycle_state}")
        self.order_book.add_order(order, grid_level)
        self.logger.info(f"{order_type} order placed at {current_price} for grid level price: {grid_level.price}.")

    def _reset_grid_cycle(self, buy_grid_level):
        buy_grid_level.reset_buy_level_cycle()
        self.logger.info(f"Buy Grid level at price {buy_grid_level.price} is reset and ready for the next buy/sell cycle.")