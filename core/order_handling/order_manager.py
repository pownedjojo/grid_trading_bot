import logging, asyncio
from typing import Union
from .order import Order, OrderType, OrderSide
from ..order_handling.balance_tracker import BalanceTracker
from config.config_manager import ConfigManager
from ..order_handling.order_book import OrderBook
from ..grid_management.grid_manager import GridManager
from ..grid_management.grid_level import GridLevel
from ..validation.transaction_validator import TransactionValidator
from core.bot_management.event_bus import EventBus
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
        self.finalize_order_placement_lock = asyncio.Lock()

    async def execute_order(
        self,
        order_side: OrderSide,
        current_price: float,
        previous_price: float, 
        timestamp: Union[int, str]
    ) -> None:
        crossed_grid_level = self.grid_manager.get_crossed_grid_level(current_price, previous_price, sell=(order_side == OrderSide.SELL))

        if crossed_grid_level is None:
            self.logger.debug(f"No grid level crossed for {order_side} Order")
            return
                
        if order_side == OrderSide.BUY:
            await self._process_buy_order(crossed_grid_level, current_price, timestamp)
        else:
            await self._process_sell_order(crossed_grid_level, current_price, timestamp)
    
    async def execute_take_profit_or_stop_loss_order(
        self,
        current_price: float,
        timestamp: Union[int, str],
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
            order_result = await self.order_execution_strategy.execute_market_order(OrderSide.SELL, pair, quantity, current_price)
            
            order = Order(
                identifier=order_result.get('id', "N/A"),
                price=order_result.get('price', "N/A"),
                quantity=order_result.get('filled_qty', "N/A"),
                order_side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                timestamp=order_result.get('timestamp', timestamp)
            )
            
            self.order_book.add_order(order)
            await self.balance_tracker.update_after_sell(order.quantity, order.price)
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
        current_price: float, 
        timestamp: Union[int, str]
    ) -> None:
        try:
            quantity = self.grid_manager.get_order_size_per_grid(current_price)

            if quantity > 0:
                self.transaction_validator.validate_buy_order(self.balance_tracker.balance, quantity, current_price, grid_level)
                await self._place_order(grid_level, OrderSide.BUY, OrderType.MARKET, current_price, quantity, timestamp)
            
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
        current_price: float, 
        timestamp: Union[int, str]
    ) -> None:
        buy_grid_level = self.grid_manager.find_lowest_completed_buy_grid()

        if buy_grid_level is None:
            self.logger.debug(f"No grid level found with a completed buy order.")
            return

        try:
            buy_order = buy_grid_level.buy_orders[-1]
            quantity = min(buy_order.quantity, self.balance_tracker.crypto_balance)

            if quantity > 0:
                self.transaction_validator.validate_sell_order(self.balance_tracker.crypto_balance, buy_order.quantity, grid_level)
                await self._place_order(grid_level, OrderSide.SELL, OrderType.MARKET, current_price, quantity, timestamp)
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
        quantity: float,
        timestamp: Union[int, str]
    ) -> None:
        pair = f"{self.config_manager.get_base_currency()}/{self.config_manager.get_quote_currency()}"
        order_result = await self.order_execution_strategy.execute_market_order(order_side, pair, quantity, current_price)

        order = Order(
            identifier=order_result.get('id', "N/A"),
            price=order_result.get('price', "N/A"),
            quantity=order_result.get('filled_qty', "N/A"),
            order_side=order_side,
            order_type=order_type,
            timestamp=order_result.get('timestamp', timestamp)
        )

        if order_result.get('status') == 'filled':
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
            if order.order_side == OrderSide.BUY:
                grid_level.place_buy_order(order)
                await self.balance_tracker.update_after_buy(order.quantity, order.price)
            else:
                grid_level.place_sell_order(order)
                await self.balance_tracker.update_after_sell(order.quantity, order.price)
            
            self.order_book.add_order(order, grid_level)
            self.logger.debug(f"{order.order_side} order placed at {order.price} for grid level {grid_level.price}")