from unittest.mock import Mock, patch, AsyncMock
import pytest
from core.order_handling.order_manager import OrderManager
from core.order_handling.order import Order, OrderType
from core.grid_management.grid_level import GridLevel
from core.services.exchange_interface import ExchangeInterface
from config.trading_mode import TradingMode
from core.order_handling.execution_strategy.live_order_execution_strategy import LiveOrderExecutionStrategy
from core.order_handling.execution_strategy.backtest_order_execution_strategy import BacktestOrderExecutionStrategy
from core.validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError, GridLevelNotReadyError
from utils.notification.notification_handler import NotificationHandler
from utils.notification.notification_content import NotificationType

class TestOrderManager:
    @pytest.fixture
    def mock_dependencies(self):
        return {
            'config_manager': Mock(),
            'grid_manager': Mock(),
            'transaction_validator': Mock(),
            'balance_tracker': AsyncMock(),
            'order_book': Mock(), 
            'notification_handler': AsyncMock()
        }

    @pytest.fixture
    def mock_exchange_service(self):
        return Mock(spec=ExchangeInterface)

    @pytest.fixture(params=["backtest", "live"])
    def order_manager(self, request, mock_dependencies, mock_exchange_service):
        if request.param == "live":
            strategy = LiveOrderExecutionStrategy(exchange_service=mock_exchange_service)
        else:
            strategy = BacktestOrderExecutionStrategy()

        return OrderManager(
            config_manager=mock_dependencies['config_manager'],
            grid_manager=mock_dependencies['grid_manager'],
            transaction_validator=mock_dependencies['transaction_validator'],
            balance_tracker=mock_dependencies['balance_tracker'],
            order_book=mock_dependencies['order_book'],
            notification_handler=mock_dependencies['notification_handler'],
            order_execution_strategy=strategy
        )

    @pytest.mark.asyncio
    async def test_execute_order_no_grid_cross(self, order_manager, mock_dependencies):
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = None
        
        await order_manager.execute_order(OrderType.BUY, 1000, 900, "2024-01-01T00:00:00Z")
        
        mock_dependencies['grid_manager'].detect_grid_level_crossing.assert_called_once()
        mock_dependencies['transaction_validator'].validate_buy_order.assert_not_called()
        mock_dependencies['balance_tracker'].update_after_buy.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_buy_order_with_valid_grid_cross(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = 1000
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        mock_dependencies['grid_manager'].get_order_size_per_grid.return_value = 1000
        mock_dependencies['balance_tracker'].balance = 10000

        if isinstance(order_manager.order_execution_strategy, LiveOrderExecutionStrategy):
            mock_order_result = {
                'status': 'filled',
                'price': 1000,
                'filled_qty': 1000,
                'timestamp': "2024-01-01T00:00:00Z"
            }
            order_manager.order_execution_strategy.execute_order = AsyncMock(return_value=mock_order_result)

        await order_manager.execute_order(OrderType.BUY, 1000, 900, "2024-01-01T00:00:00Z")

        mock_dependencies['grid_manager'].get_grid_level.assert_called_once_with(1000)
        mock_dependencies['transaction_validator'].validate_buy_order.assert_called_once_with(
            mock_dependencies['balance_tracker'].balance, 1000, 1000, grid_level
        )
        mock_dependencies['balance_tracker'].update_after_buy.assert_called_once_with(1000, 1000)

    @pytest.mark.asyncio
    async def test_execute_sell_order_with_valid_grid_cross(self, order_manager, mock_dependencies):
        # Set up mocks
        grid_level = Mock()
        buy_order = Mock(quantity=5)
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = 1000
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        mock_dependencies['balance_tracker'].crypto_balance = 5

        buy_grid_level = Mock()
        buy_grid_level.buy_orders = [buy_order]
        mock_dependencies['grid_manager'].find_lowest_completed_buy_grid.return_value = buy_grid_level

        if isinstance(order_manager.order_execution_strategy, LiveOrderExecutionStrategy):
            mock_order_result = {
                'status': 'filled',
                'price': 1000,
                'filled_qty': buy_order.quantity,
                'timestamp': "2024-01-01T00:00:00Z"
            }
            order_manager.order_execution_strategy.execute_order = AsyncMock(return_value=mock_order_result)

        order_placed = Order(1000, 5, OrderType.SELL, "2024-01-01T00:00:00Z")
        await order_manager.execute_order(OrderType.SELL, 1000, 1100, "2024-01-01T00:00:00Z")

        mock_dependencies['grid_manager'].get_grid_level.assert_called_once_with(1000)
        mock_dependencies['transaction_validator'].validate_sell_order.assert_called_once_with(
            mock_dependencies['balance_tracker'].crypto_balance, 
            buy_order.quantity, 
            grid_level
        )
        mock_dependencies['balance_tracker'].update_after_sell.assert_called_once_with(buy_order.quantity, 1000)

        if isinstance(order_manager.order_execution_strategy, LiveOrderExecutionStrategy):
            mock_dependencies['notification_handler'].async_send_notification.assert_called_once_with(
                NotificationType.ORDER_PLACED,
                order_details=str( Order(1000, 5, OrderType.SELL, "2024-01-01T00:00:00Z"))
            )

    @pytest.mark.asyncio
    async def test_execute_take_profit(self, order_manager, mock_dependencies):
        mock_dependencies['balance_tracker'].crypto_balance = 5
        mock_order_result = {'price': 2000, 'filled_qty': 5, 'timestamp': "2024-01-01T00:00:00Z", 'status': 'filled'}
        order_manager.order_execution_strategy = AsyncMock()
        order_manager.order_execution_strategy.execute_order.return_value = mock_order_result

        await order_manager.execute_take_profit_or_stop_loss_order(2000, "2024-01-01T00:00:00Z", take_profit_order=True)

        order_manager.order_execution_strategy.execute_order.assert_called_once_with(
            OrderType.SELL, 
            mock_dependencies['config_manager'].get_pair(), 
            5,
            2000
        )

        mock_dependencies['balance_tracker'].update_after_sell.assert_called_once_with(5, 2000)
        mock_dependencies['order_book'].add_order.assert_called_once()
        order_added = mock_dependencies['order_book'].add_order.call_args[0][0]
        mock_dependencies['notification_handler'].async_send_notification.assert_called_once_with(
            NotificationType.TAKE_PROFIT_TRIGGERED,
            order_details=str(order_added)
        )
        assert order_added.order_type == OrderType.SELL, "Expected order type to be SELL for take profit"
        assert order_added.price == 2000, "Expected order price to be 2000 for take profit"
        assert order_added.quantity == 5, "Expected order quantity to match crypto balance"
        assert order_added.timestamp == "2024-01-01T00:00:00Z", "Expected timestamp to match input"

    @pytest.mark.asyncio
    async def test_execute_stop_loss(self, order_manager, mock_dependencies):
        mock_dependencies['balance_tracker'].crypto_balance = 5
        mock_order_result = {'price': 1500, 'filled_qty': 5, 'timestamp': "2024-01-01T00:00:00Z", 'status': 'filled'}
        order_manager.order_execution_strategy = AsyncMock()
        order_manager.order_execution_strategy.execute_order.return_value = mock_order_result

        await order_manager.execute_take_profit_or_stop_loss_order(1500, "2024-01-01T00:00:00Z", stop_loss_order=True)

        order_manager.order_execution_strategy.execute_order.assert_called_once_with(
            OrderType.SELL, 
            mock_dependencies['config_manager'].get_pair(), 
            5,
            1500
        )

        mock_dependencies['balance_tracker'].update_after_sell.assert_called_once_with(5, 1500)
        mock_dependencies['order_book'].add_order.assert_called_once()
        order_added = mock_dependencies['order_book'].add_order.call_args[0][0]
        mock_dependencies['notification_handler'].async_send_notification.assert_called_once_with(
            NotificationType.STOP_LOSS_TRIGGERED,
            order_details=str(order_added)
        )
        assert order_added.order_type == OrderType.SELL, "Expected order type to be SELL for stop loss"
        assert order_added.price == 1500, "Expected order price to be 1500 for stop loss"
        assert order_added.quantity == 5, "Expected order quantity to match crypto balance"
        assert order_added.timestamp == "2024-01-01T00:00:00Z", "Expected timestamp to match input"

    @pytest.mark.asyncio
    async def test_process_buy_order_insufficient_balance(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['balance_tracker'].balance = 100
        mock_dependencies['transaction_validator'].validate_buy_order.side_effect = InsufficientBalanceError

        await order_manager._process_buy_order(grid_level, 1000, "2024-01-01T00:00:00Z")

        mock_dependencies['balance_tracker'].update_after_buy.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_sell_order_insufficient_crypto(self, order_manager, mock_dependencies):
        grid_level = Mock()
        buy_grid_level = Mock()
        mock_dependencies['grid_manager'].find_lowest_completed_buy_grid.return_value = buy_grid_level
        mock_dependencies['transaction_validator'].validate_sell_order.side_effect = InsufficientCryptoBalanceError

        await order_manager._process_sell_order(grid_level, 1000, "2024-01-01T00:00:00Z")

        mock_dependencies['balance_tracker'].update_after_sell.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_buy_order_grid_level_not_ready(self, order_manager, mock_dependencies):
        grid_level = Mock(spec=GridLevel)
        grid_level.can_place_buy_order.return_value = False
        grid_level.price = 1000
        grid_level.cycle_state = "not_ready" 
        order_manager.order_execution_strategy = AsyncMock()
        order_manager.balance_tracker = mock_dependencies['balance_tracker']
        order_manager.config_manager = mock_dependencies['config_manager']

        with pytest.raises(GridLevelNotReadyError, match=f"Grid level {grid_level.price} is not ready for a buy order, current state: {grid_level.cycle_state}"):
            await order_manager._verify_order_conditions(grid_level, OrderType.BUY)

        grid_level.can_place_buy_order.assert_called_once()
        order_manager.order_execution_strategy.execute_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_buy_orders_for_sell(self, order_manager, mock_dependencies):
        grid_level = Mock()
        buy_order_1 = Mock(quantity=2)
        buy_order_2 = Mock(quantity=3)
        mock_dependencies['balance_tracker'].crypto_balance = 5

        
        mock_dependencies['grid_manager'].find_lowest_completed_buy_grid.return_value = Mock(buy_orders=[buy_order_1, buy_order_2])
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        
        await order_manager.execute_order(OrderType.SELL, 1000, 1100, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_sell_order.assert_called_once_with(
            mock_dependencies['balance_tracker'].crypto_balance, 3, grid_level
        )
    
    @pytest.mark.asyncio
    async def test_zero_quantity_order(self, order_manager, mock_dependencies):
        mock_dependencies['balance_tracker'].balance = 0
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = 1000
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        
        await order_manager.execute_order(OrderType.BUY, 1000, 900, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_buy_order.assert_not_called()
        mock_dependencies['balance_tracker'].update_after_buy.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_extreme_price_fluctuation(self, order_manager, mock_dependencies):
        grid_level = Mock()

        mock_dependencies['grid_manager'].detect_grid_level_crossing.side_effect = [None, 5000]
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level

        await order_manager.execute_order(OrderType.BUY, 5000, 1000, "2024-01-01T00:00:00Z")

        mock_dependencies['grid_manager'].detect_grid_level_crossing.assert_called_once_with(5000, 1000, sell=False)
        mock_dependencies['grid_manager'].get_grid_level.assert_not_called()  # No grid crossing, so no grid level

        # Reset mock call tracking for the second execution
        mock_dependencies['grid_manager'].detect_grid_level_crossing.reset_mock()

        await order_manager.execute_order(OrderType.BUY, 5000, 4000, "2024-01-01T00:01:00Z")
        mock_dependencies['grid_manager'].detect_grid_level_crossing.assert_called_once_with(5000, 4000, sell=False)
        mock_dependencies['grid_manager'].get_grid_level.assert_called_once_with(5000)

    @pytest.mark.asyncio
    async def test_negative_price_handling(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = None

        # Simulate a negative price scenario
        await order_manager.execute_order(OrderType.BUY, -1000, 1000, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_buy_order.assert_not_called()
        mock_dependencies['balance_tracker'].update_after_buy.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_crypto_balance_for_sell(self, order_manager, mock_dependencies):
        grid_level = Mock()
        buy_order = Mock(quantity=5)
        mock_dependencies['grid_manager'].find_lowest_completed_buy_grid.return_value = Mock(buy_orders=[buy_order])
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        mock_dependencies['balance_tracker'].crypto_balance = 3  # Partial balance available

        if isinstance(order_manager.order_execution_strategy, LiveOrderExecutionStrategy):
            mock_order_result = {
                'status': 'filled',
                'price': 1000,
                'filled_qty': 3,  # Partial quantity sold
                'timestamp': "2024-01-01T00:00:00Z"
            }
            order_manager.order_execution_strategy.execute_order = AsyncMock(return_value=mock_order_result)

        await order_manager.execute_order(OrderType.SELL, 1000, 1100, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_sell_order.assert_called_once_with(3, buy_order.quantity, grid_level)
        mock_dependencies['balance_tracker'].update_after_sell.assert_called_once_with(3, 1000)
        
    @pytest.mark.asyncio
    async def test_minimal_price_difference(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = None

        # Test minimal price difference (e.g., only $1 difference)
        await order_manager.execute_order(OrderType.BUY, 1000, 999, "2024-01-01T00:00:00Z")
        
        mock_dependencies['grid_manager'].get_grid_level.assert_not_called()
        mock_dependencies['transaction_validator'].validate_buy_order.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_high_volume_trades(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = 1000
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        mock_dependencies['grid_manager'].get_order_size_per_grid.return_value = 10000
        mock_dependencies['balance_tracker'].balance = 1000000  # Large balance for a large trade

        if isinstance(order_manager.order_execution_strategy, LiveOrderExecutionStrategy):
            mock_order_result = {
                'status': 'filled',
                'price': 900,
                'filled_qty': 10000,
                'timestamp': "2024-01-01T00:00:00Z"
            }
            order_manager.order_execution_strategy.execute_order = AsyncMock(return_value=mock_order_result)

        await order_manager.execute_order(OrderType.BUY, 1000, 900, "2024-01-01T00:00:00Z")

        mock_dependencies['transaction_validator'].validate_buy_order.assert_called_once()
        mock_dependencies['balance_tracker'].update_after_buy.assert_called_once()