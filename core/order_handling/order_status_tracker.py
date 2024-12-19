import asyncio, logging
from core.bot_management.event_bus import EventBus, Events
from core.order_handling.order_book import OrderBook
from core.order_handling.order import Order, OrderStatus

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
        polling_interval: float = 15.0,
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
        self._active_tasks = set()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _track_open_order_statuses(self) -> None:
        """
        Periodically checks the statuses of open orders and updates their states.
        """
        try:
            while True:
                await self._process_open_orders()
                await asyncio.sleep(self.polling_interval)

        except asyncio.CancelledError:
            self.logger.info("OrderStatusTracker monitoring task was cancelled.")
            await self._cancel_active_tasks()

        except Exception as error:
            self.logger.error(f"Unexpected error in OrderStatusTracker: {error}")

    async def _process_open_orders(self) -> None:
        """
        Processes open orders by querying their statuses and handling state changes.
        """
        open_orders = self.order_book.get_open_orders()
        tasks = [self._create_task(self._query_and_handle_order(order)) for order in open_orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Error during order processing: {result}", exc_info=True)

    async def _query_and_handle_order(self, order):
        """
        Query order and handling state changes if needed.
        """
        try:
            order_status = await self.order_execution_strategy.get_order(order.identifier, order.symbol)
            self._handle_order_status_change(order, order_status)

        except Exception as error:
            self.logger.error(f"Failed to query status for order {order.identifier}: {error}", exc_info=True)

    def _handle_order_status_change(
        self,
        local_order: Order,
        remote_order: Order,
    ) -> None:
        """
        Handles changes in the status of an order by comparing the local order state 
        with the latest data fetched from the exchange.

        Args:
            local_order: The local `Order` object being tracked.
            remote_order: The latest `Order` object fetched from the exchange.
        
        Raises:
            ValueError: If critical fields (e.g., status) are missing from the remote order.
        """
        try:
            if remote_order.status == OrderStatus.UNKNOWN:
                self.logger.error(f"Missing 'status' in remote order object: {remote_order}", exc_info=True)
                raise ValueError("Order data from the exchange is missing the 'status' field.")

            if remote_order.status == OrderStatus.CLOSED:
                self.order_book.update_order_status(local_order.identifier, OrderStatus.CLOSED)
                self.event_bus.publish_sync(Events.ORDER_COMPLETED, local_order)
                self.logger.info(f"Order {local_order.identifier} completed.")

            if remote_order.status == OrderStatus.CANCELED:
                self.order_book.update_order_status(local_order.identifier, OrderStatus.CANCELED)
                self.event_bus.publish_sync(Events.ORDER_CANCELLED, local_order)
                self.logger.warning(f"Order {local_order.identifier} was canceled.")

            if remote_order.status == OrderStatus.OPEN:  # Still open
                if remote_order.filled > 0:
                    self.logger.info(f"Order {remote_order.identifier} partially filled. Filled: {remote_order.filled}, Remaining: {remote_order.remaining}.")
                else:
                    self.logger.debug(f"Order {remote_order.identifier} is still open. No fills yet.")

            else:
                self.logger.warning(f"Unhandled order status '{remote_order.status}' for order {remote_order.identifier}.")

        except Exception as e:
            self.logger.error(f"Error handling order status change: {e}", exc_info=True)

    def _create_task(self, coro):
        """
        Creates a managed asyncio task and adds it to the active task set.

        Args:
            coro: Coroutine to be scheduled as a task.
        """
        task = asyncio.create_task(coro)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task

    async def _cancel_active_tasks(self):
        """
        Cancels all active tasks tracked by the tracker.
        """
        for task in self._active_tasks:
            task.cancel()
        await asyncio.gather(*self._active_tasks, return_exceptions=True)
        self._active_tasks.clear()

    def start_tracking(self) -> None:
        """
        Starts the order tracking task.
        """
        if self._monitoring_task and not self._monitoring_task.done():
            self.logger.warning("OrderStatusTracker is already running.")
            return
        self._monitoring_task = asyncio.create_task(self._track_open_order_statuses())
        self.logger.info("OrderStatusTracker has started tracking open orders.")

    async def stop_tracking(self) -> None:
        """
        Stops the order tracking task.
        """
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                self.logger.info("OrderStatusTracker monitoring task was cancelled.")
            await self._cancel_active_tasks()
            self._monitoring_task = None
            self.logger.info("OrderStatusTracker has stopped tracking open orders.")