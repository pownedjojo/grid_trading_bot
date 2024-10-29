import logging
from typing import Union
from .order import Order, OrderType
from ..order_handling.balance_tracker import BalanceTracker
from config.config_manager import ConfigManager
from ..order_handling.order_execution_strategy import OrderExecutionStrategy
from ..order_handling.order_book import OrderBook
from ..grid_management.grid_manager import GridManager
from ..grid_management.grid_level import GridLevel
from ..validation.transaction_validator import TransactionValidator
from ..validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError, GridLevelNotReadyError
from .order_execution_strategy import OrderExecutionStrategy

class OrderManager:
    def __init__(
        self, 
        config_manager: ConfigManager, 
        grid_manager: GridManager,
        transaction_validator: TransactionValidator, 
        balance_tracker: BalanceTracker, 
        order_book: OrderBook,
        order_execution_strategy: OrderExecutionStrategy
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.grid_manager = grid_manager
        self.transaction_validator = transaction_validator
        self.balance_tracker = balance_tracker
        self.order_book = order_book
        self.order_execution_strategy = order_execution_strategy

    def execute_order(self, order_type: OrderType, current_price: float, previous_price: float, timestamp: Union[int, str]) -> None:
        grid_price = self.grid_manager.detect_grid_level_crossing(current_price, previous_price, sell=(order_type == OrderType.SELL))

        if grid_price is None:
            self.logger.info(f"No grid level crossed for {order_type}.")
            return
        
        grid_level_crossed = self.grid_manager.get_grid_level(grid_price)
        if order_type == OrderType.BUY:
            self._process_buy_order(grid_level_crossed, current_price, timestamp)
        elif order_type == OrderType.SELL:
            self._process_sell_order(grid_level_crossed, current_price, timestamp)
    
    def execute_take_profit_or_stop_loss_order(self, current_price: float, timestamp: Union[int, str], take_profit_order: bool = False, stop_loss_order: bool = False) -> None:
        if take_profit_order or stop_loss_order:
            order = Order(current_price, self.balance_tracker.crypto_balance, OrderType.SELL, timestamp)
            self.order_book.add_order(order)
            self.balance_tracker.sell_all(current_price)
            event = "Take profit" if take_profit_order else "Stop loss"
            self.logger.info(f"{event} triggered at {current_price}")

    def _process_buy_order(self, grid_level: GridLevel, current_price: float, timestamp: Union[int, str]) -> None:
        try:
            quantity = self.grid_manager.get_order_size_per_grid(current_price)

            if quantity > 0:
                self.transaction_validator.validate_buy_order(self.balance_tracker.balance, quantity, current_price, grid_level)
                self._verify_order_conditions(grid_level, OrderType.BUY)
                self._place_order(grid_level, OrderType.BUY, current_price, quantity, timestamp)

        except (InsufficientBalanceError, GridLevelNotReadyError) as e:
            self.logger.info(f"Cannot process buy order: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while processing buy order: {e}")
    
    def _process_sell_order(self, grid_level: GridLevel, current_price: float, timestamp: Union[int, str]) -> None:
        buy_grid_level = self.grid_manager.find_lowest_completed_buy_grid()

        if buy_grid_level is None:
            self.logger.info(f"No grid level found with a completed buy order.")
            return

        try:
            buy_order = buy_grid_level.buy_orders[-1]
            quantity = min(buy_order.quantity, self.balance_tracker.crypto_balance)

            if quantity > 0:
                self.transaction_validator.validate_sell_order(self.balance_tracker.crypto_balance, buy_order.quantity, grid_level)
                self._verify_order_conditions(grid_level, OrderType.SELL)
                self._place_order(grid_level, OrderType.SELL, current_price, quantity, timestamp)
                self.grid_manager.reset_grid_cycle(buy_grid_level)

        except (GridLevelNotReadyError, InsufficientCryptoBalanceError) as e:
            self.logger.info(f"Cannot process sell order: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while processing sell order: {e}")

    def _verify_order_conditions(self, grid_level: GridLevel, order_type: OrderType) -> None:
        if order_type == OrderType.BUY:
            if not grid_level.can_place_buy_order():
                raise GridLevelNotReadyError(f"Grid level {grid_level.price} is not ready for a buy order, current state: {grid_level.cycle_state}")
        else:  # SELL
            if not grid_level.can_place_sell_order():
                raise GridLevelNotReadyError(f"Grid level {grid_level.price} is not ready for a sell order, current state: {grid_level.cycle_state}")
    
    def _place_order(self, grid_level: GridLevel, order_type: OrderType, current_price: float, quantity: float, timestamp: Union[int, str]) -> None:
        try:
            order_result = self.order_execution_strategy.execute_order(order_type, self.config_manager.get_pair(), quantity, current_price)

            order = Order(
                price=order_result.get('price', current_price),
                quantity=order_result.get('filled_qty', quantity),
                order_type=order_type,
                timestamp=order_result.get('timestamp', timestamp)
            )

            if order_result.get('status') == 'filled' or order_result.get('status') == 'partially_filled':
                self._handle_order_placement(order, grid_level, order_type)
            else:
                self.logger.warning(f"Order could not be fully filled. Status: {order_result.get('status')}")

        except Exception as e:
            self.logger.error(f"Failed to place {order_type} order at {current_price}: {e}")

    def _handle_order_placement(self, order: Order, grid_level: GridLevel, order_type: OrderType) -> None:
        if order_type == OrderType.BUY:
            grid_level.place_buy_order(order)
            self.balance_tracker.update_after_buy(order.quantity, order.price)
        else:
            grid_level.place_sell_order(order)
            self.balance_tracker.update_after_sell(order.quantity, order.price)
        
        self.order_book.add_order(order, grid_level)
        self.logger.info(f"{order_type} order placed at {order.price} for grid level {grid_level.price}.")