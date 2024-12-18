import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch
from core.bot_management.grid_trading_bot import GridTradingBot
from core.bot_management.notification.notification_handler import NotificationHandler
from core.bot_management.event_bus import EventBus, Events
from core.bot_management.health_check import HealthCheck
from utils.constants import RESSOURCE_THRESHOLDS

class TestHealthCheck(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = Mock(spec=GridTradingBot)
        self.notification_handler = Mock(spec=NotificationHandler)
        self.event_bus = Mock(spec=EventBus)
        self.health_check = HealthCheck(
            bot=self.bot,
            notification_handler=self.notification_handler,
            event_bus=self.event_bus,
            check_interval=1  # Set a low interval for testing
        )

    async def test_start_and_stop(self):
        self.health_check._perform_checks = AsyncMock()
        self.health_check._is_running = False  # Ensure it starts

        start_task = asyncio.create_task(self.health_check.start())
        await asyncio.sleep(0.1)  # Give it time to start

        self.assertTrue(self.health_check._is_running)
        self.health_check._perform_checks.assert_called_once()

        self.health_check._is_running = False
        await asyncio.sleep(0.1)  # Allow for loop termination
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        self.assertFalse(self.health_check._is_running)

    async def test_stop_event(self):
        self.health_check._is_running = True
        reason = "User initiated stop"

        self.health_check._handle_stop(reason)

        self.assertFalse(self.health_check._is_running)

    async def test_start_event(self):
        self.health_check._is_running = False
        self.health_check.start = AsyncMock()

        await self.health_check._handle_start("User initiated start")

        self.health_check.start.assert_awaited_once()

    async def test_perform_checks_success(self):
        self.bot.get_bot_health_status = AsyncMock(return_value={"strategy": True, "exchange_status": "ok"})
        self.health_check._check_resource_usage = Mock(return_value={"cpu": 10, "memory": 10, "disk": 10})

        self.health_check._check_and_alert_bot_health = AsyncMock()
        self.health_check._check_and_alert_resource_usage = AsyncMock()

        await self.health_check._perform_checks()

        self.health_check._check_and_alert_bot_health.assert_awaited_with({"strategy": True, "exchange_status": "ok"})
        self.health_check._check_and_alert_resource_usage.assert_awaited_with({"cpu": 10, "memory": 10, "disk": 10})

    async def test_check_and_alert_bot_health_with_alerts(self):
        health_status = {"strategy": False, "exchange_status": "maintenance"}
        self.health_check._send_alert = AsyncMock()

        await self.health_check._check_and_alert_bot_health(health_status)

        self.health_check._send_alert.assert_awaited_once_with("Trading strategy has encountered issues. | Exchange status is not ok: maintenance")

    async def test_check_and_alert_bot_health_no_alerts(self):
        health_status = {"strategy": True, "exchange_status": "ok"}
        self.health_check._send_alert = AsyncMock()

        await self.health_check._check_and_alert_bot_health(health_status)

        self.health_check._send_alert.assert_not_awaited()

    async def test_check_and_alert_resource_usage_with_alerts(self):
        usage = {"cpu": 95, "memory": 85, "disk": 10}
        self.health_check._send_alert = AsyncMock()

        await self.health_check._check_and_alert_resource_usage(usage)

        expected_message = "CPU usage is high: 95% (Threshold: 90%) | MEMORY usage is high: 85% (Threshold: 80%)"
        self.health_check._send_alert.assert_awaited_once_with(expected_message)

    async def test_check_and_alert_resource_usage_no_alerts(self):
        usage = {"cpu": 10, "memory": 10, "disk": 10}
        self.health_check._send_alert = AsyncMock()

        await self.health_check._check_and_alert_resource_usage(usage)

        self.health_check._send_alert.assert_not_awaited()

    @patch("psutil.cpu_percent", return_value=95)
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    @patch("psutil.Process")
    def test_check_resource_usage(self, mock_process, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        mock_virtual_memory.return_value.percent = 85
        mock_disk_usage.return_value.percent = 10
        mock_process.return_value.cpu_percent.return_value = 20
        mock_process.return_value.memory_percent.return_value = 30

        usage = self.health_check._check_resource_usage()

        self.assertEqual(usage["cpu"], 95)
        self.assertEqual(usage["memory"], 85)
        self.assertEqual(usage["disk"], 10)
        self.assertEqual(usage["bot_cpu"], 20)
        self.assertEqual(usage["bot_memory"], 30)

    async def test_send_alert(self):
        self.notification_handler.async_send_notification = AsyncMock()
        message = "Test Alert"

        await self.health_check._send_alert(message)

        self.notification_handler.async_send_notification.assert_awaited_once_with("Health Check Alert", message=message)

    async def test_start_already_running(self):
        self.health_check._is_running = True
        self.health_check.logger.warning = Mock()

        await self.health_check.start()

        self.health_check.logger.warning.assert_called_once_with("HealthCheck is already running.")

    def test_handle_stop_when_not_running(self):
        self.health_check._is_running = False
        self.health_check.logger.warning = Mock()

        self.health_check._handle_stop("Already stopped")

        self.health_check.logger.warning.assert_called_once_with("HealthCheck is not running.")