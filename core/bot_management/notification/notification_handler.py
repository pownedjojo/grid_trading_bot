from typing import List, Optional, Union
import apprise, logging, asyncio
from concurrent.futures import ThreadPoolExecutor
from .notification_content import NotificationType
from config.trading_mode import TradingMode
from core.bot_management.event_bus import EventBus, Events
from core.order_handling.order import Order

class NotificationHandler:
    _executor = ThreadPoolExecutor(max_workers=3)

    def __init__(
        self, 
        event_bus: EventBus,
        urls: Optional[List[str]], 
        trading_mode: TradingMode
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.event_bus = event_bus
        self.enabled = bool(urls) and trading_mode in {TradingMode.LIVE, TradingMode.PAPER_TRADING}
        self.lock = asyncio.Lock()
        self.apprise_instance = apprise.Apprise() if self.enabled else None
        
        if self.enabled:
            self.event_bus.subscribe(Events.ORDER_COMPLETED, self._send_notification_on_order_completed)

            for url in urls:
                self.apprise_instance.add(url)

    def send_notification(
        self, 
        content: Union[NotificationType, str],
        **kwargs
    ) -> None:
        if self.enabled and self.apprise_instance:
            if isinstance(content, NotificationType):
                title = content.value.title
                message_template = content.value.message
                required_placeholders = {key.strip("{}") for key in message_template.split() if "{" in key and "}" in key}
                missing_placeholders = required_placeholders - kwargs.keys()

                if missing_placeholders:
                    self.logger.warning(f"Missing placeholders for notification: {missing_placeholders}. " "Defaulting to 'N/A' for missing values.")

                message = message_template.format(**{key: kwargs.get(key, 'N/A') for key in required_placeholders})
            else:
                title = "Notification"
                message = content

            self.apprise_instance.notify(title=title, body=message)

    async def async_send_notification(
        self, 
        content: Union[NotificationType, str], 
        **kwargs
    ) -> None:
        async with self.lock:
            loop = asyncio.get_running_loop()
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(self._executor, lambda: self.send_notification(content, **kwargs)),
                    timeout=5
                )
            except Exception as e:
                self.logger.error(f"Failed to send notification: {str(e)}")
    
    async def _send_notification_on_order_completed(self, order: Order) -> None:
        await self.async_send_notification(NotificationType.ORDER_PLACED, order_details=str(order))