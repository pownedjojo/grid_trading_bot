import pytest, unittest
from unittest.mock import AsyncMock, Mock, patch
from core.order_handling.order_status_tracker import OrderStatusTracker
from core.bot_management.event_bus import Events
from core.order_handling.order import OrderStatus

class TestOrderStatusTracker:
    @pytest.fixture
    def setup_tracker(self):
        order_book = Mock()
        order_execution_strategy = Mock()
        event_bus = Mock()
        tracker = OrderStatusTracker(
            order_book=order_book,
            order_execution_strategy=order_execution_strategy,
            event_bus=event_bus,
            polling_interval=1.0
        )
        return tracker, order_book, order_execution_strategy, event_bus

    @pytest.mark.asyncio
    async def test_process_open_orders_success(self, setup_tracker):
        tracker, order_book, order_execution_strategy, _ = setup_tracker
        mock_order = Mock(identifier="order_1", status=OrderStatus.OPEN)
        mock_remote_order = Mock(identifier="order_1", status=OrderStatus.CLOSED)

        order_book.get_open_orders.return_value = [mock_order]
        order_execution_strategy.get_order = AsyncMock(return_value=mock_remote_order)
        tracker._handle_order_status_change = Mock()

        await tracker._process_open_orders()

        order_execution_strategy.get_order.assert_awaited_once_with("order_1")
        tracker._handle_order_status_change.assert_called_once_with(mock_order, mock_remote_order)

    @pytest.mark.asyncio
    async def test_process_open_orders_failure(self, setup_tracker):
        tracker, order_book, order_execution_strategy, _ = setup_tracker
        mock_order = Mock(identifier="order_1", status=OrderStatus.OPEN)
    
        order_book.get_open_orders.return_value = [mock_order]
        order_execution_strategy.get_order = AsyncMock(side_effect=Exception("Failed to fetch order"))
    
        with patch.object(tracker.logger, "error") as mock_logger_error:
            await tracker._process_open_orders()
    
            order_execution_strategy.get_order.assert_awaited_once_with("order_1")
            mock_logger_error.assert_called_once_with("Failed to query status for order order_1: Failed to fetch order")

    def test_handle_order_status_change_closed(self, setup_tracker):
        tracker, order_book, _, event_bus = setup_tracker
        mock_local_order = Mock(identifier="order_1")
        mock_remote_order = Mock(identifier="order_1", status=OrderStatus.CLOSED)
    
        with patch.object(tracker.logger, "info") as mock_logger_info:
            tracker._handle_order_status_change(mock_local_order, mock_remote_order)
    
            order_book.update_order_status.assert_called_once_with("order_1", OrderStatus.CLOSED)
            event_bus.publish_sync.assert_called_once_with(Events.ORDER_COMPLETED, mock_local_order)
            mock_logger_info.assert_called_once_with("Order order_1 completed.")

    def test_handle_order_status_change_canceled(self, setup_tracker):
        tracker, order_book, _, event_bus = setup_tracker
        mock_local_order = Mock(identifier="order_1")
        mock_remote_order = Mock(identifier="order_1", status=OrderStatus.CANCELED)

        with patch.object(tracker.logger, "warning") as mock_logger_warning:
            tracker._handle_order_status_change(mock_local_order, mock_remote_order)

            order_book.update_order_status.assert_called_once_with("order_1", OrderStatus.CANCELED)
            event_bus.publish_sync.assert_called_once_with(Events.ORDER_CANCELLED, mock_local_order)

            mock_logger_warning.assert_any_call("Order order_1 was canceled.")

    def test_handle_order_status_change_unknown_status(self, setup_tracker):
        tracker, _, _, event_bus = setup_tracker
        mock_local_order = Mock(identifier="order_1")
        mock_remote_order = Mock(identifier="order_1", status=OrderStatus.UNKNOWN)

        with pytest.raises(ValueError, match="Order data from the exchange is missing the 'status' field."):
            tracker._handle_order_status_change(mock_local_order, mock_remote_order)

    def test_handle_order_status_change_open(self, setup_tracker):
        tracker, _, _, _ = setup_tracker
        mock_local_order = Mock(identifier="order_1")
        mock_remote_order = Mock(identifier="order_1", status=OrderStatus.OPEN, filled=0)

        with patch.object(tracker.logger, "debug") as mock_logger_debug:
            tracker._handle_order_status_change(mock_local_order, mock_remote_order)

            mock_logger_debug.assert_called_once_with("Order order_1 is still open. No fills yet.")

    def test_handle_order_status_change_partially_filled(self, setup_tracker):
        tracker, _, _, _ = setup_tracker
        mock_local_order = Mock(identifier="order_1")
        mock_remote_order = Mock(identifier="order_1", status=OrderStatus.OPEN, filled=0.5, remaining=0.5)

        with patch.object(tracker.logger, "info") as mock_logger_info:
            tracker._handle_order_status_change(mock_local_order, mock_remote_order)

            mock_logger_info.assert_called_once_with("Order order_1 partially filled. Filled: 0.5, Remaining: 0.5.")

    def test_handle_order_status_change_unhandled_status(self, setup_tracker):
        tracker, _, _, _ = setup_tracker
        mock_local_order = Mock(identifier="order_1")
        mock_remote_order = Mock(identifier="order_1", status="unexpected_status")

        with patch.object(tracker.logger, "warning") as mock_logger_warning:
            tracker._handle_order_status_change(mock_local_order, mock_remote_order)

            mock_logger_warning.assert_called_once_with("Unhandled order status 'unexpected_status' for order order_1.")