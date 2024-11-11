import asyncio, psutil, logging
from core.bot_management.grid_trading_bot import GridTradingBot
from core.bot_management.notification.notification_handler import NotificationHandler
from utils.constants import RESSOURCE_THRESHOLDS

class HealthCheck:
    def __init__(
        self, 
        bot: GridTradingBot, 
        notification_handler: NotificationHandler,
        stop_event: asyncio.Event,
        check_interval: int = 60
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bot = bot
        self.notification_handler = notification_handler
        self.stop_event = stop_event
        self.check_interval = check_interval
    
    async def start(self):
        while not self.stop_event.is_set():
            await self._perform_checks()
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.check_interval)
            except asyncio.TimeoutError:
                print("timeout")
                continue

    async def _perform_checks(self):
        try:
            bot_health = await self.bot.get_bot_health_status()
            await self._check_and_alert_bot_health(bot_health)

            ressource_usage = self._check_ressource_usage()            
            await self._check_and_alert_ressource_usage(ressource_usage)

        except Exception as e:
            self.logger.error(f"Health check encountered an error: {e}")
            await self._send_alert(f"Health check error: {e}")
    
    async def _check_and_alert_bot_health(self, health_status: dict):
        alerts = []

        if not health_status["strategy"]:
            alerts.append("Trading strategy has encountered issues.")
        if not health_status["exchange_status"] == "ok":
            alerts.append(f"Exchange status is not ok: {health_status['exchange_status']}")

        if alerts:
            await self._send_alert(" | ".join(alerts))

    async def _check_and_alert_ressource_usage(self, usage: dict):
        alerts = []

        for resource, threshold in RESSOURCE_THRESHOLDS.items():
            if usage.get(resource, 0) > threshold:
                message = f"{resource.upper()} usage is high: {usage[resource]}% (Threshold: {threshold}%)"
                self.logger.warning(message)
                alerts.append(message)

        if alerts:
            await self._send_alert(" | ".join(alerts))

    def _check_ressource_usage(self) -> dict:
        usage = {
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent
        }
        process = psutil.Process()
        usage["bot_cpu"] = process.cpu_percent()
        usage["bot_memory"] = process.memory_percent()
        return usage

    async def _send_alert(self, message: str):
        await self.notification_handler.async_send_notification("Health Check Alert", message=message)