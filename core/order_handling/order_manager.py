import logging, asyncio
from typing import Union
from .order import Order, OrderStatus, OrderType, OrderSide
from ..order_handling.balance_tracker import BalanceTracker
from config.config_manager import ConfigManager
from ..order_handling.order_book import OrderBook
from ..grid_management.grid_manager import GridManager
from ..grid_management.grid_level import GridLevel
from ..validation.transaction_validator import TransactionValidator
from core.bot_management.event_bus import EventBus, Events
from ..validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError, GridLevelNotReadyError
from .execution_strategy.order_execution_strategy import OrderExecutionStrategy
from core.bot_management.notification.notification_handler import NotificationHandler
from core.bot_management.notification.notification_content import NotificationType
from .exceptions import OrderExecutionFailedError

class OrderManager:
    def __init__(
        self, 
        config_manager: ConfigManager, 
        grid_manager: GridManager,
        transaction_validator: TransactionValidator, 
        balance_tracker: BalanceTracker, 
        order_book: OrderBook,
        event_bus: EventBus,
        order_execution_strategy: OrderExecutionStrategy,
        notification_handler: NotificationHandler
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.grid_manager = grid_manager
        self.transaction_validator = transaction_validator
        self.balance_tracker = balance_tracker
        self.order_book = order_book
        self.event_bus = event_bus
        self.order_execution_strategy = order_execution_strategy
        self.notification_handler = notification_handler
        self.pair = f"{self.config_manager.get_base_currency()}/{self.config_manager.get_quote_currency()}"

        ## TODO: Lock to remove ?
        self.finalize_order_placement_lock = asyncio.Lock()
        self.event_bus.subscribe(Events.ORDER_COMPLETED, self._on_order_completed)
    
    async def initialize_grid_orders(self):
        """
        Places initial buy orders for grid levels below the current price.
        """
        for price in self.grid_manager.sorted_buy_grids:
            grid_level = self.grid_manager.grid_levels[price]

            if grid_level.can_place_buy_order():
                try:
                    order_quantity = self.grid_manager.get_order_size_per_grid(price)
                    self.logger.info(f"Placing initial buy limit order at grid level {price} for {order_quantity} {self.pair}.")

                    order = await self.order_execution_strategy.execute_limit_order(OrderSide.BUY, self.pair, order_quantity, price)

                    if order is None:
                        self.logger.error(f"Failed to place buy order at {price}: No order returned.")
                        continue

                    self.grid_manager.mark_buy_order_pending(grid_level, order)
                    self.order_book.add_order(order, grid_level)

                except OrderExecutionFailedError as e:
                    self.logger.error(f"Failed to initialize buy order at grid level {price} - {str(e)}", exc_info=True)

                except Exception as e:
                    self.logger.error(f"Unexpected error during buy order initialization at grid level {price}: {e}", exc_info=True)
    
    async def _on_order_completed(self, order: Order) -> None:
        """
        Handles completed orders and places paired orders as needed.

        Args:
            order: The completed Order instance.
        """
        try:
            grid_level = self.order_book.get_grid_level_for_order(order)

            if not grid_level:
                self.logger.warning(f"No grid level found for completed order {order.identifier}.")
                return

            if order.side == OrderSide.BUY:
                self.logger.info(f"Buy order completed at grid level {grid_level.price}.")
                self.grid_manager.complete_buy_order(grid_level)
                paired_sell_level = self.grid_manager.get_paired_sell_level(grid_level)

                if paired_sell_level and paired_sell_level.can_place_sell_order():
                    self.logger.info(f"Placing sell limit order at grid level {paired_sell_level.price} for quantity {order.filled}")
                    sell_order = await self.order_execution_strategy.execute_limit_order(OrderSide.SELL, self.pair, order.filled, paired_sell_level.price)
                    
                    if sell_order is None:
                        ## TODO: handle this case
                        self.logger.error(f"Failed to place sell order at {paired_sell_level.price}: No order returned.")
                        return
        
                    self.grid_manager.mark_sell_order_pending(paired_sell_level, sell_order)
                    self.order_book.add_order(sell_order, paired_sell_level)

            elif order.side == OrderSide.SELL:
                self.logger.info(f"Sell order completed at grid level {grid_level.price}.")
                self.grid_manager.complete_sell_order(grid_level)

        except Exception as e:
            self.logger.error(f"Error handling completed order {order.identifier}: {e}")

    async def execute_order(
        self,
        order_side: OrderSide,
        current_price: float,
        previous_price: float
    ) -> None:
        crossed_grid_level = self.grid_manager.get_crossed_grid_level(current_price, previous_price, sell=(order_side == OrderSide.SELL))

        if crossed_grid_level is None:
            self.logger.debug(f"No grid level crossed for {order_side} Order")
            return
                
        if order_side == OrderSide.BUY:
            await self._process_buy_order(crossed_grid_level, current_price)
        else:
            await self._process_sell_order(crossed_grid_level, current_price)
    
    async def execute_take_profit_or_stop_loss_order(
        self,
        current_price: float,
        take_profit_order: bool = False,
        stop_loss_order: bool = False
    ) -> None:
        if not (take_profit_order or stop_loss_order):
            self.logger.warning("No take profit or stop loss action specified.")
            return

        event = "Take profit" if take_profit_order else "Stop loss"
        pair = f"{self.config_manager.get_base_currency()}/{self.config_manager.get_quote_currency()}"

        try:
            quantity = self.balance_tracker.crypto_balance
            order = await self.order_execution_strategy.execute_market_order(OrderSide.SELL, pair, quantity, current_price)

            if not order:
                self.logger.error(f"Order execution failed: {order}")
                raise Exception

            self.order_book.add_order(order)
            await self.balance_tracker.update_after_sell(order.amount, order.price)
            await self.notification_handler.async_send_notification(
                NotificationType.TAKE_PROFIT_TRIGGERED if take_profit_order else NotificationType.STOP_LOSS_TRIGGERED,
                order_details=str(order)
            )            
            self.logger.debug(f"{event} triggered at {current_price} and sell order executed.")
        
        except OrderExecutionFailedError as e:
            self.logger.error(f"Order execution failed: {str(e)}")
            await self.notification_handler.async_send_notification(NotificationType.ORDER_FAILED, error_details=f"Failed to place {event} order: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to execute {event} sell order at {current_price}: {e}")
            await self.notification_handler.async_send_notification(NotificationType.ERROR_OCCURRED, error_details=f"Failed to place {event} order: {e}")

    async def _process_buy_order(
        self,
        grid_level: GridLevel, 
        current_price: float
    ) -> None:
        try:
            quantity = self.grid_manager.get_order_size_per_grid(current_price)

            if quantity > 0:
                self.transaction_validator.validate_buy_order(self.balance_tracker.balance, quantity, current_price, grid_level)
                await self._place_order(grid_level, OrderSide.BUY, OrderType.MARKET, current_price, quantity)
            
        except GridLevelNotReadyError as e:
            self.logger.debug(f"{e}")

        except InsufficientBalanceError as e:
            self.logger.warning(e)
        
        except OrderExecutionFailedError as e:
            self.logger.error(f"Order execution failed: {str(e)}")
            await self.notification_handler.async_send_notification(NotificationType.ORDER_FAILED, error_details=f"Failed to place order: {e}")

        except Exception as e:
            self.logger.error(f"Unexpected error while processing buy order: {e}")
            await self.notification_handler.async_send_notification(NotificationType.ERROR_OCCURRED, error_details=f"Unexpected error while processing buy order: {e}")
    
    async def _process_sell_order(
        self, 
        grid_level: GridLevel, 
        current_price: float
    ) -> None:
        buy_grid_level = self.grid_manager.find_lowest_completed_buy_grid()

        if buy_grid_level is None:
            self.logger.debug(f"No grid level found with a completed buy order.")
            return

        try:
            buy_order = buy_grid_level.buy_orders[-1]
            quantity = min(buy_order.amount, self.balance_tracker.crypto_balance)

            if quantity > 0:
                self.transaction_validator.validate_sell_order(self.balance_tracker.crypto_balance, buy_order.amount, grid_level)
                await self._place_order(grid_level, OrderSide.SELL, OrderType.MARKET, current_price, quantity)
                self.grid_manager.reset_grid_cycle(buy_grid_level)
        
        except GridLevelNotReadyError as e:
            self.logger.debug(f"Cannot process sell order: {e}")

        except InsufficientCryptoBalanceError as e:
            self.logger.warning(f"Cannot process sell order: {e}")
        
        except OrderExecutionFailedError as e:
            self.logger.error(f"Order execution failed: {str(e)}")
            await self.notification_handler.async_send_notification(NotificationType.ORDER_FAILED, error_details=f"Failed to place order: {e}")

        except Exception as e:
            self.logger.error(f"Unexpected error while processing sell order: {e}")
            await self.notification_handler.async_send_notification(NotificationType.ERROR_OCCURRED, error_details=f"Unexpected error while processing sell order: {e}")
    
    async def _place_order(
        self, 
        grid_level: GridLevel, 
        order_side: OrderSide, 
        order_type: OrderType, 
        current_price: float, 
        quantity: float
    ) -> None:
        pair = f"{self.config_manager.get_base_currency()}/{self.config_manager.get_quote_currency()}"
        order = await self.order_execution_strategy.execute_market_order(order_side, pair, quantity, current_price)            

        if order is not None and order.status == OrderStatus.CLOSED:
            await self._finalize_order_placement(order, grid_level)              
            await self.notification_handler.async_send_notification(NotificationType.ORDER_PLACED, order_details=str(order))
        else:
            raise OrderExecutionFailedError("Order could not be fully filled", order_side, order_type, pair, quantity, current_price)

    async def _finalize_order_placement(
        self, 
        order: Order, 
        grid_level: GridLevel
    ) -> None:
        async with self.finalize_order_placement_lock:
            if order.side == OrderSide.BUY:
                grid_level.place_buy_order(order)
                await self.balance_tracker.update_after_buy(order.amount, order.price)
            else:
                grid_level.place_sell_order(order)
                await self.balance_tracker.update_after_sell(order.amount, order.price)
            
            self.order_book.add_order(order, grid_level)
            self.logger.debug(f"{order.side} order placed at {order.price} for grid level {grid_level.price}")