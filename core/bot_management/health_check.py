import asyncio, psutil, logging
from core.bot_management.grid_trading_bot import GridTradingBot
from core.bot_management.notification.notification_handler import NotificationHandler
from core.bot_management.event_bus import EventBus, Events
from utils.constants import RESSOURCE_THRESHOLDS

class HealthCheck:
    """
    Periodically checks the bot's health and system resource usage and sends alerts if thresholds are exceeded.
    """

    def __init__(
        self, 
        bot: GridTradingBot, 
        notification_handler: NotificationHandler,
        event_bus: EventBus,
        check_interval: int = 60
    ):
        """
        Initializes the HealthCheck.

        Args:
            bot: The GridTradingBot instance to monitor.
            notification_handler: The NotificationHandler for sending alerts.
            event_bus: The EventBus instance for listening to bot lifecycle events.
            check_interval: Time interval (in seconds) between health checks.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bot = bot
        self.notification_handler = notification_handler
        self.event_bus = event_bus
        self.check_interval = check_interval
        self._is_running = False
        self.event_bus.subscribe(Events.STOP_BOT, self._handle_stop)
        self.event_bus.subscribe(Events.START_BOT, self._handle_start)
    
    async def start(self):
        """
        Starts the health check monitoring loop.
        """
        if self._is_running:
            self.logger.warning("HealthCheck is already running.")
            return

        self._is_running = True
        self.logger.info("HealthCheck started.")

        try:
            while self._is_running:
                await self._perform_checks()
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            self.logger.info("HealthCheck task cancelled.")
            
        except Exception as e:
            self.logger.error(f"Unexpected error in HealthCheck: {e}")
            await self._send_alert(f"HealthCheck error: {e}")

    async def _perform_checks(self):
        """
        Performs bot health and resource usage checks.
        """
        try:
            bot_health = await self.bot.get_bot_health_status()
            await self._check_and_alert_bot_health(bot_health)

            ressource_usage = self._check_ressource_usage()            
            await self._check_and_alert_ressource_usage(ressource_usage)

        except Exception as e:
            self.logger.error(f"Health check encountered an error: {e}")
            await self._send_alert(f"Health check error: {e}")
    
    async def _check_and_alert_bot_health(self, health_status: dict):
        """
        Checks the bot's health status and sends alerts if necessary.

        Args:
            health_status: A dictionary containing the bot's health status.
        """
        alerts = []

        if not health_status["strategy"]:
            alerts.append("Trading strategy has encountered issues.")
        if not health_status["exchange_status"] == "ok":
            alerts.append(f"Exchange status is not ok: {health_status['exchange_status']}")

        if alerts:
            await self._send_alert(" | ".join(alerts))

    async def _check_and_alert_ressource_usage(self, usage: dict):
        """
        Checks system resource usage and sends alerts if thresholds are exceeded.

        Args:
            usage: A dictionary containing resource usage metrics.
        """
        alerts = []

        for resource, threshold in RESSOURCE_THRESHOLDS.items():
            if usage.get(resource, 0) > threshold:
                message = f"{resource.upper()} usage is high: {usage[resource]}% (Threshold: {threshold}%)"
                self.logger.warning(message)
                alerts.append(message)

        if alerts:
            await self._send_alert(" | ".join(alerts))

    def _check_ressource_usage(self) -> dict:
        """
        Collects system resource usage metrics.

        Returns:
            A dictionary containing CPU, memory, disk, and bot-specific resource usage.
        """
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
        """
        Sends an alert via the NotificationHandler.

        Args:
            message: The alert message to send.
        """
        await self.notification_handler.async_send_notification("Health Check Alert", message=message)
    
    def _handle_stop(self, reason: str) -> None:
        """
        Handles the STOP_BOT event to stop the HealthCheck.

        Args:
            reason: The reason for stopping the bot.
        """
        if not self._is_running:
            self.logger.warning("HealthCheck is not running.")
            return

        self._is_running = False
        self.logger.info(f"HealthCheck stopped: {reason}")

    async def _handle_start(self, reason: str) -> None:
        """
        Handles the START_BOT event to start the HealthCheck.

        Args:
            reason: The reason for starting the bot.
        """
        if self._is_running:
            self.logger.warning("HealthCheck is already running.")
            return

        self.logger.info(f"HealthCheck starting: {reason}")
        await self.start()