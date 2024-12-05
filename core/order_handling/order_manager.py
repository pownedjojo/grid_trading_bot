import logging
from typing import Union
from .order import Order, OrderSide, OrderStatus
from ..order_handling.balance_tracker import BalanceTracker
from config.config_manager import ConfigManager
from ..order_handling.order_book import OrderBook
from ..grid_management.grid_manager import GridManager
from ..validation.transaction_validator import TransactionValidator
from core.bot_management.event_bus import EventBus, Events
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

                    self.transaction_validator.validate_buy_order(self.balance_tracker.balance, order_quantity, price, grid_level)
                    self.balance_tracker.reserve_funds_for_buy(order_quantity * price)

                    order = await self.order_execution_strategy.execute_limit_order(OrderSide.BUY, self.pair, order_quantity, price)

                    if order is None:
                        self.logger.error(f"Failed to place buy order at {price}: No order returned.")
                        continue

                    self.grid_manager.mark_buy_order_pending(grid_level, order)
                    self.order_book.add_order(order, grid_level)

                except OrderExecutionFailedError as e:
                    self.logger.error(f"Failed to initialize buy order at grid level {price} - {str(e)}", exc_info=True)
                    await self.notification_handler.async_send_notification(NotificationType.ORDER_FAILED, error_details=f"Failed to place order: {e}")

                except Exception as e:
                    self.logger.error(f"Unexpected error during buy order initialization at grid level {price}: {e}", exc_info=True)
                    await self.notification_handler.async_send_notification(NotificationType.ERROR_OCCURRED, error_details=f"Failed to place order: {e}")
    
    async def _on_order_completed(
        self, 
        order: Order
    ) -> None:
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
                    self.transaction_validator.validate_sell_order(self.balance_tracker.crypto_balance, order.filled, paired_sell_level)
                    sell_order = await self.order_execution_strategy.execute_limit_order(OrderSide.SELL, self.pair, order.filled, paired_sell_level.price)
                    
                    if sell_order is None:
                        await self.notification_handler.async_send_notification(NotificationType.ORDER_FAILED)       
                        self.logger.error(f"Failed to place sell order at {paired_sell_level.price}: No order returned.")
                        return
        
                    self.grid_manager.mark_sell_order_pending(paired_sell_level, sell_order)
                    self.order_book.add_order(sell_order, paired_sell_level)

            elif order.side == OrderSide.SELL:
                self.logger.info(f"Sell order completed at grid level {grid_level.price}.")
                self.grid_manager.complete_sell_order(grid_level)
        
        except OrderExecutionFailedError as e:
            self.logger.error(f"Failed while handling completed order - {str(e)}", exc_info=True)
            await self.notification_handler.async_send_notification(NotificationType.ORDER_FAILED, error_details=f"Failed to place order: {e}")

        except Exception as e:
            self.logger.error(f"Error handling completed order {order.identifier}: {e}")

    async def execute_take_profit_or_stop_loss_order(
        self,
        current_price: float,
        take_profit_order: bool = False,
        stop_loss_order: bool = False
    ) -> None:
        """
        Executes a sell order triggered by either a take-profit or stop-loss event.

        This method checks whether a take-profit or stop-loss condition has been met
        and places a market sell order accordingly. It uses the crypto balance tracked
        by the `BalanceTracker` and sends notifications upon success or failure.

        Args:
            current_price (float): The current market price triggering the event.
            take_profit_order (bool): Indicates whether this is a take-profit event.
            stop_loss_order (bool): Indicates whether this is a stop-loss event.
        """
        if not (take_profit_order or stop_loss_order):
            self.logger.warning("No take profit or stop loss action specified.")
            return

        event = "Take profit" if take_profit_order else "Stop loss"
        try:
            quantity = self.balance_tracker.crypto_balance
            order = await self.order_execution_strategy.execute_market_order(OrderSide.SELL, self.pair, quantity, current_price)

            if not order:
                self.logger.error(f"Order execution failed: {order}")
                raise Exception

            self.order_book.add_order(order)
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
    
    async def simulate_order_fills(
        self, 
        high_price: float, 
        low_price: float, 
        timestamp: Union[int, str]
    ) -> None:
        """
        Simulates the execution of limit orders based on the high and low prices of the current step.

        Args:
            high_price: The highest price reached in this time interval.
            low_price: The lowest price reached in this time interval.
            timestamp: The current timestamp in the backtest simulation.
        """
        pending_orders = self.order_book.get_open_orders()

        for order in pending_orders:
            if (order.side == OrderSide.BUY and order.price >= low_price) or (order.side == OrderSide.SELL and order.price <= high_price):
                order.filled = order.amount
                order.remaining = 0.0
                order.status = OrderStatus.CLOSED
                order.last_trade_timestamp = int(timestamp)

                self.logger.info(f"Simulated fill for {order.side.value.upper()} order at price {order.price} with amount {order.amount}. Filled at timestamp {timestamp}")
                await self.event_bus.publish(Events.ORDER_COMPLETED, order)