import logging, asyncio
from typing import Callable, Dict, List, Any, Awaitable, Union

class Events:
    """
    Defines event types for the EventBus.
    """
    ORDER_COMPLETED = "order_completed"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_PENDING = "order_pending"
    START_BOT = "start_bot"
    STOP_BOT = "stop_bot"

class EventBus:
    """
    A simple event bus for managing pub-sub interactions with support for both sync and async publishing.
    """

    def __init__(self):
        """
        Initializes the EventBus with an empty subscriber list.
        """
        self.subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def subscribe(self, event_type: str, callback: Union[Callable[[Any], None], Callable[[Any], Awaitable[None]]]) -> None:
        """
        Subscribes a callback to a specific event type.
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        self.logger.info(f"Callback subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """
        Unsubscribes a callback from a specific event type.
        """
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            self.logger.info(f"Callback unsubscribed from event: {event_type}")
            # Remove the event type if no callbacks are left
            if not self.subscribers[event_type]:
                del self.subscribers[event_type]
        else:
            self.logger.warning(f"Attempted to unsubscribe non-existing callback from event: {event_type}")

    def clear(self, event_type: str = None) -> None:
        """
        Clears all subscribers for a specific event type or all subscribers if no event type is specified.
        """
        if event_type:
            if event_type in self.subscribers:
                del self.subscribers[event_type]
                self.logger.info(f"Cleared all subscribers for event: {event_type}")
            else:
                self.logger.warning(f"Attempted to clear non-existing event type: {event_type}")
        else:
            self.subscribers.clear()
            self.logger.info("Cleared all subscribers for all events")

    async def publish(self, event_type: str, data: Any) -> None:
        """
        Publishes an event asynchronously to all subscribers.
        """
        if event_type in self.subscribers:
            self.logger.info(f"Publishing async event: {event_type} with data: {data}")
            tasks = []
            for callback in self.subscribers[event_type]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(self._safe_invoke_async(callback, data))
                else:
                    tasks.append(self._safe_invoke_sync(callback, data))
            await asyncio.gather(*tasks, return_exceptions=True)

    def publish_sync(self, event_type: str, data: Any) -> None:
        """
        Publishes an event synchronously to all subscribers.
        """
        if event_type in self.subscribers:
            self.logger.info(f"Publishing sync event: {event_type} with data: {data}")
            loop = asyncio.get_event_loop()
            for callback in self.subscribers[event_type]:
                if asyncio.iscoroutinefunction(callback):
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(self._safe_invoke_async(callback, data), loop)
                    else:
                        loop.run_until_complete(self._safe_invoke_async(callback, data))
                else:
                    self._safe_invoke_sync(callback, data)

    async def _safe_invoke_async(self, callback: Callable[[Any], None], data: Any) -> None:
        """
        Safely invokes an async callback, suppressing and logging any exceptions.
        """
        try:
            await callback(data)
        except Exception as e:
            self.logger.error(f"Error in async subscriber callback: {e}", exc_info=True)

    def _safe_invoke_sync(self, callback: Callable[[Any], None], data: Any) -> None:
        """
        Safely invokes a sync callback, suppressing and logging any exceptions.
        """
        try:
            callback(data)
        except Exception as e:
            self.logger.error(f"Error in sync subscriber callback: {e}", exc_info=True)