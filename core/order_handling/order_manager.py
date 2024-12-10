import logging
from typing import Union
import pandas as pd
from .order import Order, OrderSide, OrderStatus
from ..order_handling.balance_tracker import BalanceTracker
from config.config_manager import ConfigManager
from ..order_handling.order_book import OrderBook
from ..grid_management.grid_manager import GridManager
from ..grid_management.grid_level import GridLevel
from ..validation.transaction_validator import TransactionValidator
from core.bot_management.event_bus import EventBus, Events
from .execution_strategy.order_execution_strategy import OrderExecutionStrategy
from core.bot_management.notification.notification_handler import NotificationHandler
from core.bot_management.notification.notification_content import NotificationType
from strategies.strategy_type import StrategyType
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
        self.strategy_type: StrategyType = self.config_manager.get_strategy_type()
        self.event_bus.subscribe(Events.ORDER_COMPLETED, self._on_order_completed)
    
    async def initialize_grid_orders(
        self, 
        current_price: float
    ):
        """
        Places initial buy orders for grid levels below the current price.
        """
        for price in self.grid_manager.sorted_buy_grids:
            if price >= current_price:
                self.logger.warning(f"Skipping grid level at price: {price} for BUY order: Above current price.")
                continue

            grid_level = self.grid_manager.grid_levels[price]

            if self.grid_manager.can_place_order(grid_level, OrderSide.BUY):
                try:
                    order_quantity = self.grid_manager.get_order_size_for_grid_level(price)
                    self.logger.info(f"Placing initial buy limit order at grid level {price} for {order_quantity} {self.pair}.")
                    self.transaction_validator.validate_buy_order(self.balance_tracker.balance, order_quantity, price, grid_level)
                    order = await self.order_execution_strategy.execute_limit_order(OrderSide.BUY, self.pair, order_quantity, price)

                    if order is None:
                        self.logger.error(f"Failed to place buy order at {price}: No order returned.")
                        continue

                    self.balance_tracker.reserve_funds_for_buy(order_quantity * price)
                    self.grid_manager.mark_order_pending(grid_level, order)
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
                self.logger.warning(f"Could not handle Order completion - No grid level found for the given completed order {order}")
                return

            await self._handle_order_completion(order, grid_level)

        except OrderExecutionFailedError as e:
            self.logger.error(f"Failed while handling completed order - {str(e)}", exc_info=True)
            await self.notification_handler.async_send_notification(NotificationType.ORDER_FAILED, error_details=f"Failed to place order: {e}")

        except Exception as e:
            self.logger.error(f"Error handling completed order {order.identifier}: {e}", exc_info=True)

    async def _handle_order_completion(
        self, 
        order: Order, 
        grid_level: GridLevel
    ) -> None:
        """
        Handles completed orders.

        Args:
            order: The completed Order instance.
            grid_level: The grid level associated with the order.
        """
        if order.side == OrderSide.BUY:
            self.logger.info(f"Buy order completed at grid level {grid_level.price}.")
            self.grid_manager.complete_order(grid_level, OrderSide.BUY)
            paired_sell_level = self.grid_manager.get_paired_sell_level(grid_level)

            if paired_sell_level and self.grid_manager.can_place_order(paired_sell_level, OrderSide.SELL):
                self.logger.info(f"Placing sell limit order at grid level {paired_sell_level.price} for quantity {order.filled}")
                self.transaction_validator.validate_sell_order(self.balance_tracker.crypto_balance, order.filled, paired_sell_level)
                sell_order = await self.order_execution_strategy.execute_limit_order(OrderSide.SELL, self.pair, order.filled, paired_sell_level.price)

                if sell_order:
                    self.grid_manager.pair_grid_levels(grid_level, paired_sell_level)
                    self.balance_tracker.reserve_funds_for_sell(sell_order.amount)
                    self.grid_manager.mark_order_pending(paired_sell_level, order)
                    self.order_book.add_order(sell_order, paired_sell_level)
                else:
                    self.logger.error(f"Failed to place sell order at {paired_sell_level.price}")

        elif order.side == OrderSide.SELL:
            self.logger.info(f"Sell order completed at grid level {grid_level.price}.")
            self.grid_manager.complete_order(grid_level, OrderSide.SELL)
            paired_buy_level = grid_level.paired_grid_level

            if paired_buy_level is None or not self.grid_manager.can_place_order(paired_buy_level, OrderSide.BUY):
                self.logger.error(f"No paired buy grid level for grid_level: {grid_level} - unable to place limit buy order.")
                return

            self.logger.info(f"Placing Buy limit order at grid level {paired_buy_level.price} for {order.amount} {self.pair}.")
            self.transaction_validator.validate_buy_order(self.balance_tracker.balance, order.amount, paired_buy_level.price, paired_buy_level)
            order = await self.order_execution_strategy.execute_limit_order(OrderSide.BUY, self.pair, order.amount, paired_buy_level.price)
            self.balance_tracker.reserve_funds_for_buy(order.amount * paired_buy_level.price)
            self.grid_manager.mark_order_pending(grid_level, order)
            self.order_book.add_order(order, paired_buy_level)
            self.grid_manager.unpair_grid_levels(buy_grid_level=paired_buy_level, sell_grid_level=grid_level)

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
        timestamp: Union[int, pd.Timestamp]
    ) -> None:
        """
        Simulates the execution of limit orders based on crossed grid levels within the high-low price range.

        Args:
            high_price: The highest price reached in this time interval.
            low_price: The lowest price reached in this time interval.
            timestamp: The current timestamp in the backtest simulation.
        """
        timestamp_val = int(timestamp.timestamp()) if isinstance(timestamp, pd.Timestamp) else int(timestamp)
        pending_orders = self.order_book.get_open_orders()
        crossed_buy_levels = [level for level in self.grid_manager.sorted_buy_grids if low_price <= level <= high_price]
        crossed_sell_levels = [level for level in self.grid_manager.sorted_sell_grids if low_price <= level <= high_price]

        self.logger.debug(f"Simulating fills: High {high_price}, Low {low_price}, Pending orders: {len(pending_orders)}")
        self.logger.debug(f"Crossed buy levels: {crossed_buy_levels}, Crossed sell levels: {crossed_sell_levels}")

        for order in pending_orders:
            if order.side == OrderSide.BUY and order.price in crossed_buy_levels:
                await self._simulate_fill(order, timestamp_val)

            elif order.side == OrderSide.SELL and order.price in crossed_sell_levels:
                await self._simulate_fill(order, timestamp_val)

    async def _simulate_fill(
        self, 
        order: Order, 
        timestamp: int
    ) -> None:
        """
        Simulates filling an order by marking it as completed and publishing an event.

        Args:
            order: The order to simulate a fill for.
            timestamp: The timestamp at which the order is filled.
        """
        order.filled = order.amount
        order.remaining = 0.0
        order.status = OrderStatus.CLOSED
        order.last_trade_timestamp = timestamp
        self.logger.info(f"Simulated fill for {order.side.value.upper()} order at price {order.price} with amount {order.amount}. Filled at timestamp {timestamp}")
        await self.event_bus.publish(Events.ORDER_COMPLETED, order)