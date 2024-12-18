import pytest
from unittest.mock import patch, AsyncMock, Mock
from core.order_handling.order import Order, OrderStatus, OrderType, OrderSide
from core.bot_management.notification.notification_handler import NotificationHandler
from core.bot_management.notification.notification_content import NotificationType
from config.trading_mode import TradingMode
from core.bot_management.event_bus import EventBus


class TestNotificationHandler:
    @pytest.fixture
    def notification_handler_enabled(self):
        event_bus = EventBus()
        urls = ["json://localhost:8080/path"]
        trading_mode = TradingMode.LIVE
        handler = NotificationHandler(event_bus=event_bus, urls=urls, trading_mode=trading_mode)
        handler.enabled = True
        return handler

    @pytest.fixture
    def notification_handler_disabled(self):
        event_bus = EventBus()
        return NotificationHandler(event_bus=event_bus, urls=None, trading_mode=TradingMode.BACKTEST)

    @patch("apprise.Apprise")
    def test_notification_handler_enabled_initialization(self, mock_apprise):
        event_bus = EventBus()
        handler = NotificationHandler(event_bus=event_bus, urls=["mock://example.com"], trading_mode=TradingMode.LIVE)
        assert handler.enabled is True
        mock_apprise.return_value.add.assert_called_once_with("mock://example.com")

    @patch("apprise.Apprise")
    def test_notification_handler_disabled_initialization(self, mock_apprise):
        event_bus = EventBus()
        handler = NotificationHandler(event_bus=event_bus, urls=None, trading_mode=TradingMode.BACKTEST)
        assert handler.enabled is False
        mock_apprise.assert_not_called()

    @patch("apprise.Apprise.notify")
    @pytest.mark.asyncio
    async def test_send_notification_with_predefined_content(self, mock_notify, notification_handler_enabled):
        handler = notification_handler_enabled
        order_placed = Order(
            identifier="123", 
            price=1000, 
            filled=5,
            average=1000,
            amount=5,
            remaining=0,
            status=OrderStatus.OPEN,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            timestamp="2024-01-01T00:00:00Z",
            last_trade_timestamp="2024-01-01T00:00:00Z",
            datetime="2024-01-01T00:00:00Z",
            symbol="",
            time_in_force=""
        )
        order_details = (
            f"Id={order_placed.identifier}, side={order_placed.side}, type={order_placed.order_type}, "
            f"price={order_placed.price}, quantity={order_placed.filled}, timestamp={order_placed.timestamp}, state=OrderStatus.OPEN"
        )

        handler.send_notification(NotificationType.ORDER_PLACED, order_details=order_details)

        mock_notify.assert_called_once_with(
            title="Order Placed",
            body=(
                "New order placed successfully:\n"
                "Id=123, side=OrderSide.BUY, type=OrderType.MARKET, price=1000, quantity=5, timestamp=2024-01-01T00:00:00Z, state=OrderStatus.OPEN"
            )
        )

    @patch("apprise.Apprise.notify")
    @pytest.mark.asyncio
    async def test_send_notification_with_custom_message(self, mock_notify, notification_handler_enabled):
        handler = notification_handler_enabled
        handler.send_notification("Custom notification message")

        mock_notify.assert_called_once_with(
            title="Notification",
            body="Custom notification message"
        )

    @patch("apprise.Apprise.notify")
    @pytest.mark.asyncio
    async def test_send_notification_disabled(self, mock_notify, notification_handler_disabled):
        handler = notification_handler_disabled

        handler.send_notification(NotificationType.ORDER_PLACED, order_type="BUY", price=1200, quantity=0.5, timestamp="2024-01-01T12:00:00Z", status="filled")

        mock_notify.assert_not_called()

    @patch("apprise.Apprise.notify")
    @patch("core.bot_management.notification.notification_handler.logging.Logger.warning")
    @pytest.mark.asyncio
    async def test_send_notification_with_missing_placeholder(self, mock_log_warning, mock_notify, notification_handler_enabled):
        handler = notification_handler_enabled

        handler.send_notification(NotificationType.ORDER_PLACED)

        mock_log_warning.assert_called_once_with("Missing placeholders for notification: {'order_details'}. Defaulting to 'N/A' for missing values.")
        mock_notify.assert_called_once_with(title="Order Placed", body="New order placed successfully:\nN/A")

    @patch("apprise.Apprise.notify")
    @pytest.mark.asyncio
    async def test_send_notification_with_order_failed(self, mock_notify, notification_handler_enabled):
        handler = notification_handler_enabled

        handler.send_notification(NotificationType.ORDER_FAILED, error_details="Order could not be fully filled")

        mock_notify.assert_called_once_with(title="Order Failed", body="Failed to place order:\nOrder could not be fully filled")

    @pytest.mark.asyncio
    async def test_async_send_notification_success(self, notification_handler_enabled):
        handler = notification_handler_enabled
        handler.send_notification = Mock()

        await handler.async_send_notification("Async notification message")

        handler.send_notification.assert_called_once_with("Async notification message")

    @pytest.mark.asyncio
    async def test_event_subscription_and_notification_on_order_completed(self, notification_handler_enabled):
        handler = notification_handler_enabled
        order = Order(
            identifier="123", 
            price=1000, 
            filled=5,
            average=1000,
            amount=5,
            remaining=0,
            status=OrderStatus.OPEN,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            timestamp="2024-01-01T00:00:00Z",
            last_trade_timestamp="2024-01-01T00:00:00Z",
            datetime="2024-01-01T00:00:00Z",
            symbol="",
            time_in_force=""
        )        
        handler.async_send_notification = AsyncMock()

        await handler._send_notification_on_order_completed(order)

        handler.async_send_notification.assert_called_once_with(NotificationType.ORDER_PLACED, order_details=str(order))