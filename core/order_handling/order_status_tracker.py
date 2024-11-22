import asyncio, logging
from core.bot_management.event_bus import EventBus, Events
from core.order_handling.order_book import OrderBook
from core.order_handling.order import Order, OrderState

class OrderStatusTracker:
    """
    Tracks the status of pending orders and publishes events
    when their states change (e.g., completed, canceled).
    """

    def __init__(
        self,
        order_book: OrderBook,
        order_execution_strategy,
        event_bus: EventBus,
        polling_interval: float = 5.0,
    ):
        """
        Initializes the OrderStatusTracker.

        Args:
            order_book: OrderBook instance to manage and query orders.
            order_execution_strategy: Strategy for querying order statuses from the exchange.
            event_bus: EventBus instance for publishing state change events.
            polling_interval: Time interval (in seconds) between status checks.
        """
        self.order_book = order_book
        self.order_execution_strategy = order_execution_strategy
        self.event_bus = event_bus
        self.polling_interval = polling_interval
        self._monitoring_task = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _track_order_statuses(self) -> None:
        """
        Periodically checks the statuses of pending orders and updates their states.
        """
        try:
            while True:
                self._process_pending_orders()
                await asyncio.sleep(self.polling_interval)
        except asyncio.CancelledError:
            self.logger.info("OrderStatusTracker monitoring task was cancelled.")
        except Exception as error:
            self.logger.exception(f"Unexpected error in OrderStatusTracker: {error}")

    def _process_pending_orders(self) -> None:
        """
        Processes pending orders by querying their statuses and handling state changes.
        """
        pending_orders = self.order_book.get_pending_orders()
        for order in pending_orders:
            try:
                order_status = self.order_execution_strategy.get_order_status(order.identifier)
                self._handle_order_status_change(order, order_status)
            except Exception as error:
                self.logger.error(
                    f"Failed to query status for order {order.identifier}: {error}"
                )

    def _handle_order_status_change(
        self,
        order: Order,
        order_status: str,
    ) -> None:
        """
        Handles changes in order statuses and publishes relevant events.

        Args:
            order: The Order instance being tracked.
            order_status: The new status of the order.
        """
        if order_status == "filled":
            self.order_book.update_order_state(order.identifier, OrderState.COMPLETED)
            self.event_bus.publish_sync(Events.ORDER_COMPLETED, order)
            self.logger.info(f"Order {order.identifier} completed.")
        elif order_status == "canceled":
            self.order_book.update_order_state(order.identifier, OrderState.CANCELLED)
            self.event_bus.publish_sync(Events.ORDER_CANCELLED, order)
            self.logger.warning(f"Order {order.identifier} was canceled.")

    def start_tracking(self) -> None:
        """
        Starts the order tracking task.
        """
        if not self._monitoring_task:
            self._monitoring_task = asyncio.create_task(self._track_order_statuses())
            self.logger.info("OrderStatusTracker has started tracking orders.")

    def stop_tracking(self) -> None:
        """
        Stops the order tracking task.
        """
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
            self.logger.info("OrderStatusTracker has stopped tracking orders.")