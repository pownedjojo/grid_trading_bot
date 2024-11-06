from typing import List, Optional, Union
import apprise, logging, asyncio
from concurrent.futures import ThreadPoolExecutor
from .notification_content import NotificationType
from config.trading_mode import TradingMode

class NotificationHandler:
    _executor = ThreadPoolExecutor(max_workers=3)

    def __init__(self, urls: Optional[List[str]], trading_mode: TradingMode):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enabled = bool(urls) and trading_mode in {TradingMode.LIVE, TradingMode.PAPER_TRADING}
        self.lock = asyncio.Lock()
        self.apprise_instance = apprise.Apprise() if self.enabled else None
        
        if self.enabled:
            for url in urls:
                self.apprise_instance.add(url)

    def send_notification(self, content: Union[NotificationType, str], **kwargs) -> None:
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

    async def async_send_notification(self, content: Union[NotificationType, str], **kwargs) -> None:
        async with self.lock:  # Ensures no overlapping calls
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, lambda: self.send_notification(content, **kwargs))