import pytest
from unittest.mock import patch
from core.order_handling.order import Order, OrderType
from utils.notification.notification_handler import NotificationHandler
from utils.notification.notification_content import NotificationType
from config.trading_mode import TradingMode

@pytest.mark.asyncio
class TestNotificationHandler:
    @pytest.fixture
    def notification_handler_enabled(self):
        urls = ["json://localhost:8080/path"]
        trading_mode = TradingMode.LIVE
        handler = NotificationHandler(urls=urls, trading_mode=trading_mode)
        handler.enabled = True
        return handler

    @pytest.fixture
    def notification_handler_disabled(self):
        return NotificationHandler(urls=None, trading_mode=TradingMode.BACKTEST)

    @patch("apprise.Apprise")
    def test_notification_handler_enabled_initialization(self, mock_apprise):
        handler = NotificationHandler(urls=["mock://example.com"], trading_mode=TradingMode.LIVE)
        assert handler.enabled is True
        mock_apprise.return_value.add.assert_called_once_with("mock://example.com")

    @patch("apprise.Apprise")
    def test_notification_handler_disabled_initialization(self, mock_apprise):
        handler = NotificationHandler(urls=None, trading_mode=TradingMode.BACKTEST)
        assert handler.enabled is False
        mock_apprise.assert_not_called()

    @patch("apprise.Apprise.notify")
    async def test_send_notification_with_predefined_content(self, mock_notify, notification_handler_enabled):
        handler = notification_handler_enabled
        order_placed =  Order(price=1000, quantity=5, order_type=OrderType.BUY, timestamp="2024-01-01T00:00:00Z")

        handler.send_notification(NotificationType.ORDER_PLACED,  order_details=order_placed)

        mock_notify.assert_called_once_with(
            title="Order Placed",
            body=(
                "New order placed successfully:\n"
                "(OrderType.BUY Order, price=1000, quantity=5, timestamp=2024-01-01T00:00:00Z, state=OrderState.PENDING)"
            )
        )

    @patch("apprise.Apprise.notify")
    async def test_send_notification_with_custom_message(self, mock_notify, notification_handler_enabled):
        handler = notification_handler_enabled
        
        handler.send_notification("Custom notification message")

        mock_notify.assert_called_once_with(
            title="Notification",
            body="Custom notification message"
        )

    @patch("apprise.Apprise.notify")
    async def test_send_notification_disabled(self, mock_notify, notification_handler_disabled):
        handler = notification_handler_disabled
        
        handler.send_notification(NotificationType.ORDER_PLACED, order_type="BUY", price=1200, quantity=0.5, timestamp="2024-01-01T12:00:00Z", status="filled")

        mock_notify.assert_not_called()

    @patch("apprise.Apprise.notify")
    @patch("utils.notification.notification_handler.logging.Logger.warning")
    async def test_send_notification_with_missing_placeholder(self, mock_log_warning, mock_notify, notification_handler_enabled):
        handler = notification_handler_enabled

        handler.send_notification(NotificationType.ORDER_PLACED)

        mock_log_warning.assert_called_once_with("Missing placeholders for notification: {'order_details'}. Defaulting to 'N/A' for missing values.")
        mock_notify.assert_called_once_with(title="Order Placed", body="New order placed successfully:\nN/A")

    @patch("apprise.Apprise.notify")
    async def test_send_notification_with_order_failed(self, mock_notify, notification_handler_enabled):
        handler = notification_handler_enabled

        handler.send_notification(NotificationType.ORDER_FAILED,  error_details="Order could not be fully filled")

        mock_notify.assert_called_once_with(title="Order Failed", body=("Failed to place order:\nOrder could not be fully filled"))