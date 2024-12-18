import pytest
from unittest.mock import AsyncMock, Mock
from config.trading_mode import TradingMode
from core.order_handling.order_manager import OrderManager
from core.order_handling.order import OrderSide, OrderStatus, OrderType
from core.bot_management.notification.notification_content import NotificationType
from core.order_handling.exceptions import OrderExecutionFailedError
from core.bot_management.event_bus import EventBus
from strategies.strategy_type import StrategyType

class TestOrderManager:
    @pytest.fixture
    def setup_order_manager(self):
        grid_manager = Mock()
        order_validator = Mock()
        balance_tracker = Mock()
        order_book = Mock()
        event_bus = Mock(spec=EventBus)
        order_execution_strategy = Mock()
        notification_handler = Mock()
        notification_handler.async_send_notification = AsyncMock()

        manager = OrderManager(
            grid_manager=grid_manager,
            order_validator=order_validator,
            balance_tracker=balance_tracker,
            order_book=order_book,
            event_bus=event_bus,
            order_execution_strategy=order_execution_strategy,
            notification_handler=notification_handler,
            trading_mode=TradingMode.LIVE,
            trading_pair="BTC/USD",
            strategy_type=StrategyType.HEDGED_GRID
        )
        return manager, grid_manager, order_validator, balance_tracker, order_book, event_bus, order_execution_strategy, notification_handler

    @pytest.mark.asyncio
    async def test_initialize_grid_orders_buy_orders(self, setup_order_manager):
        manager, grid_manager, order_validator, balance_tracker, _, _, order_execution_strategy, _ = setup_order_manager
        grid_manager.sorted_buy_grids = [50000, 49000, 48000]
        grid_manager.sorted_sell_grids = []
        grid_manager.grid_levels = {50000: Mock(), 49000: Mock(), 48000: Mock()}
        grid_manager.can_place_order.side_effect = lambda level, side: side == OrderSide.BUY
        order_validator.adjust_and_validate_buy_quantity.return_value = 0.01
        balance_tracker.balance = 1000
        order_execution_strategy.execute_limit_order = AsyncMock(return_value=Mock())

        await manager.initialize_grid_orders(49500)

        grid_manager.can_place_order.assert_called()
        assert order_execution_strategy.execute_limit_order.call_count == 2

    @pytest.mark.asyncio
    async def test_initialize_grid_orders_sell_orders(self, setup_order_manager):
        manager, grid_manager, order_validator, balance_tracker, _, _, order_execution_strategy, _ = setup_order_manager
        grid_manager.sorted_sell_grids = [52000, 53000, 54000]
        grid_manager.sorted_buy_grids = []
        grid_manager.grid_levels = {52000: Mock(), 53000: Mock(), 54000: Mock()}
        grid_manager.can_place_order.side_effect = lambda level, side: side == OrderSide.SELL
        order_validator.adjust_and_validate_sell_quantity.return_value = 0.01
        balance_tracker.crypto_balance = 1
        order_execution_strategy.execute_limit_order = AsyncMock(return_value=Mock())

        await manager.initialize_grid_orders(51500)

        grid_manager.can_place_order.assert_called()
        assert order_execution_strategy.execute_limit_order.call_count == 3

    @pytest.mark.asyncio
    async def test_on_order_completed(self, setup_order_manager):
        manager, _, _, _, order_book, _, _, _ = setup_order_manager
        mock_order = Mock(side=OrderSide.BUY, price=50000)
        mock_grid_level = Mock()
        order_book.get_grid_level_for_order.return_value = mock_grid_level
        manager._handle_order_completion = AsyncMock()

        await manager._on_order_completed(mock_order)

        order_book.get_grid_level_for_order.assert_called_once_with(mock_order)
        manager._handle_order_completion.assert_awaited_once_with(mock_order, mock_grid_level)

    @pytest.mark.asyncio
    async def test_on_order_completed_no_grid_level(self, setup_order_manager):
        manager, _, _, _, order_book, _, _, _ = setup_order_manager
        mock_order = Mock()

        order_book.get_grid_level_for_order.return_value = None

        await manager._on_order_completed(mock_order)

        order_book.get_grid_level_for_order.assert_called_once_with(mock_order)
    
    @pytest.mark.asyncio
    async def test_handle_order_completion_buy(self, setup_order_manager):
        manager, grid_manager, _, _, _, _, _, _ = setup_order_manager
        mock_order = Mock(side=OrderSide.BUY, filled=0.01)
        mock_grid_level = Mock(price=50000)
        grid_manager.get_paired_sell_level.return_value = Mock()
        grid_manager.can_place_order.return_value = True
        manager._place_sell_order = AsyncMock()

        await manager._handle_order_completion(mock_order, mock_grid_level)

        manager._place_sell_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_order_completion_sell(self, setup_order_manager):
        manager, _, _, _, _, _, _, _ = setup_order_manager
        mock_order = Mock(side=OrderSide.SELL, filled=0.01)
        mock_grid_level = Mock(price=50000)
        manager._get_or_create_paired_buy_level = Mock(return_value=Mock())
        manager._place_buy_order = AsyncMock()

        await manager._handle_order_completion(mock_order, mock_grid_level)

        manager._place_buy_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_perform_initial_purchase(self, setup_order_manager):
        manager, grid_manager, _, _, _, _, order_execution_strategy, _ = setup_order_manager
        grid_manager.get_initial_order_quantity.return_value = 0.01
        order_execution_strategy.execute_market_order = AsyncMock(return_value=Mock())

        await manager.perform_initial_purchase(50000)

        order_execution_strategy.execute_market_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_take_profit_or_stop_loss_order(self, setup_order_manager):
        manager, _, _, balance_tracker, _, _, order_execution_strategy, notification_handler = setup_order_manager
        balance_tracker.crypto_balance = 0.5
        order_execution_strategy.execute_market_order = AsyncMock(return_value=Mock())
        notification_handler.async_send_notification = AsyncMock()

        await manager.execute_take_profit_or_stop_loss_order(55000, take_profit_order=True)

        order_execution_strategy.execute_market_order.assert_awaited_once_with(OrderSide.SELL, manager.trading_pair, 0.5, 55000)
        notification_handler.async_send_notification.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_initialize_grid_orders_execution_failed(self, setup_order_manager):
        manager, grid_manager, order_validator, balance_tracker, _, _, order_execution_strategy, notification_handler = setup_order_manager
        grid_manager.sorted_buy_grids = [49000]
        grid_manager.sorted_sell_grids = []
        grid_manager.grid_levels = {49000: Mock()}
        grid_manager.can_place_order.return_value = True
        order_validator.adjust_and_validate_buy_quantity.return_value = 0.01
        balance_tracker.balance = 1000

        order_execution_strategy.execute_limit_order = AsyncMock(
            side_effect=OrderExecutionFailedError(
                message="Execution failed",
                order_side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                pair="BTC/USD",
                quantity=0.01,
                price=50000
            )
        )
        notification_handler.async_send_notification = AsyncMock()

        await manager.initialize_grid_orders(49500)

        notification_handler.async_send_notification.assert_awaited_once_with(
            NotificationType.ORDER_FAILED,
            error_details="Failed to place order: Execution failed"
        )

    @pytest.mark.asyncio
    async def test_initialize_grid_orders_insufficient_balance(self, setup_order_manager):
        manager, grid_manager, order_validator, balance_tracker, _, _, order_execution_strategy, _ = setup_order_manager
        grid_manager.sorted_buy_grids = [49000]
        grid_manager.sorted_sell_grids = []
        grid_manager.grid_levels = {49000: Mock()}
        grid_manager.can_place_order.return_value = True
        order_validator.adjust_and_validate_buy_quantity.side_effect = ValueError("Insufficient balance")
        balance_tracker.balance = 0  # Simulate insufficient balance
        order_execution_strategy.execute_limit_order = AsyncMock()

        await manager.initialize_grid_orders(49500)

        order_execution_strategy.execute_limit_order.assert_not_awaited()
        grid_manager.can_place_order.assert_called_once_with(grid_manager.grid_levels[49000], OrderSide.BUY)
        order_validator.adjust_and_validate_buy_quantity.assert_called_once_with(
            balance=balance_tracker.balance,
            order_quantity=grid_manager.get_order_size_for_grid_level.return_value,
            price=49000
        )
    
    @pytest.mark.asyncio
    async def test_on_order_completed_unexpected_error(self, setup_order_manager):
        manager, _, _, _, order_book, _, _, _ = setup_order_manager
        mock_order = Mock()
        order_book.get_grid_level_for_order.return_value = Mock()
        manager._handle_order_completion = AsyncMock(side_effect=Exception("Unexpected error"))

        await manager._on_order_completed(mock_order)

        manager._handle_order_completion.assert_awaited_once()

    def test_get_or_create_paired_buy_level_no_fallback(self, setup_order_manager):
        manager, grid_manager, _, _, _, _, _, _ = setup_order_manager
        mock_sell_grid_level = Mock(paired_buy_level=None)
        grid_manager.get_grid_level_below.return_value = None

        paired_buy_level = manager._get_or_create_paired_buy_level(mock_sell_grid_level)

        assert paired_buy_level is None
        grid_manager.get_grid_level_below.assert_called_once_with(mock_sell_grid_level)
    
    @pytest.mark.asyncio
    async def test_simulate_order_fills_partial_fill(self, setup_order_manager):
        manager, grid_manager, _, _, order_book, _, _, _ = setup_order_manager
        mock_order = Mock(
            side=OrderSide.BUY,
            price=48000,
            amount=0.02,
            filled=0.01,
            remaining=0.01,
            status=OrderStatus.OPEN
        )
        order_book.get_open_orders.return_value = [mock_order]
        grid_manager.sorted_buy_grids = [48000]
        grid_manager.sorted_sell_grids = []

        await manager.simulate_order_fills(49000, 47000, 1234567890)

        assert mock_order.filled == 0.02
        assert mock_order.remaining == 0.0
        assert mock_order.status == OrderStatus.CLOSED