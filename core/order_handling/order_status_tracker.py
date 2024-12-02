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
        polling_interval: float = 10.0,
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
                await self._process_pending_orders()
                await asyncio.sleep(self.polling_interval)

        except asyncio.CancelledError:
            self.logger.info("OrderStatusTracker monitoring task was cancelled.")

        except Exception as error:
            self.logger.error(f"Unexpected error in OrderStatusTracker: {error}")

    async def _process_pending_orders(self) -> None:
        """
        Processes pending orders by querying their statuses and handling state changes.
        """
        pending_orders = self.order_book.get_pending_orders()
        for order in pending_orders:
            try:
                order_status = await self.order_execution_strategy.get_order(order.identifier)
                self._handle_order_status_change(order, order_status)

            except Exception as error:
                self.logger.error(f"Failed to query status for order {order.identifier}: {error}")

    def _handle_order_status_change(
        self,
        local_order: Order,
        remote_order_data: dict,
    ) -> None:
        """
        Handles changes in the status of an order by comparing the local order state 
        with the latest data fetched from the exchange.

        Args:
            local_order: The local `Order` object being tracked.
            remote_order_data: The latest order data fetched from the exchange as a dictionary.

        Raises:
            ValueError: If critical fields are missing from the `remote_order_data`.
        """
        remote_order_status = remote_order_data.get("status")
        filled = remote_order_data.get("filled_qty", 0.0)
        remaining = remote_order_data.get("remaining_qty", 0.0)

        if remote_order_status == "unknown":
            self.logger.error(f"Missing 'status' in remote order data: {remote_order_data}")
            raise ValueError("Order data from the exchange is missing the 'status' field.")

        if remote_order_status == "filled":
            self.order_book.update_order_state(local_order.identifier, OrderState.COMPLETED)
            self.event_bus.publish_sync(Events.ORDER_COMPLETED, local_order)
            self.logger.info(f"Order {local_order.identifier} completed.")

        elif remote_order_status == "canceled":
            self.order_book.update_order_state(local_order.identifier, OrderState.CANCELLED)
            self.event_bus.publish_sync(Events.ORDER_CANCELLED, local_order)
            self.logger.warning(f"Order {local_order.identifier} was canceled.")

        elif remote_order_status == "open":
            if filled > 0:
                self.logger.info(f"Order {local_order.identifier} partially filled. Filled: {filled}, Remaining: {remaining}.")
            else:
                self.logger.debug(f"Order {local_order.identifier} is still open. No fills yet.")

        else:
            self.logger.warning(f"Unhandled order status '{remote_order_status}' for order {local_order.identifier}.")

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