from unittest.mock import Mock, patch
import pytest
from core.order_handling.order_manager import OrderManager
from core.order_handling.order import OrderType
from core.validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError, GridLevelNotReadyError

class TestOrderManager:
    @pytest.fixture
    def mock_dependencies(self):
        return {
            'config_manager': Mock(),
            'grid_manager': Mock(),
            'transaction_validator': Mock(),
            'balance_tracker': Mock(),
            'order_book': Mock()
        }

    @pytest.fixture
    def order_manager(self, mock_dependencies):
        return OrderManager(
            config_manager=mock_dependencies['config_manager'],
            grid_manager=mock_dependencies['grid_manager'],
            transaction_validator=mock_dependencies['transaction_validator'],
            balance_tracker=mock_dependencies['balance_tracker'],
            order_book=mock_dependencies['order_book']
        )

    def test_execute_order_no_grid_cross(self, order_manager, mock_dependencies):
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = None
        
        order_manager.execute_order(OrderType.BUY, 1000, 900, "2024-01-01T00:00:00Z")
        
        mock_dependencies['grid_manager'].detect_grid_level_crossing.assert_called_once()
        mock_dependencies['transaction_validator'].validate_buy_order.assert_not_called()
        mock_dependencies['balance_tracker'].update_after_buy.assert_not_called()

    def test_execute_buy_order_with_valid_grid_cross(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = 1000
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        mock_dependencies['grid_manager'].get_order_size_per_grid.return_value = 1000
        mock_dependencies['balance_tracker'].balance = 10000
        
        order_manager.execute_order(OrderType.BUY, 1000, 900, "2024-01-01T00:00:00Z")
        
        mock_dependencies['grid_manager'].get_grid_level.assert_called_once_with(1000)
        mock_dependencies['transaction_validator'].validate_buy_order.assert_called_once()
        mock_dependencies['balance_tracker'].update_after_buy.assert_called_once()

    def test_execute_sell_order_with_valid_grid_cross(self, order_manager, mock_dependencies):
        grid_level = Mock()
        buy_order = Mock(quantity=5)
        
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = 1000
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        mock_dependencies['balance_tracker'].crypto_balance = 5
        
        buy_grid_level = Mock()
        buy_grid_level.buy_orders = [buy_order]
        mock_dependencies['grid_manager'].find_lowest_completed_buy_grid.return_value = buy_grid_level
        
        order_manager.execute_order(OrderType.SELL, 1000, 1100, "2024-01-01T00:00:00Z")
        
        mock_dependencies['grid_manager'].get_grid_level.assert_called_once_with(1000)
        mock_dependencies['transaction_validator'].validate_sell_order.assert_called_once_with(
            mock_dependencies['balance_tracker'].crypto_balance, 
            buy_order.quantity, 
            grid_level
        )
        mock_dependencies['balance_tracker'].update_after_sell.assert_called_once_with(buy_order.quantity, 1000)

    def test_execute_take_profit(self, order_manager, mock_dependencies):
        mock_dependencies['balance_tracker'].crypto_balance = 5

        order_manager.execute_take_profit_or_stop_loss_order(2000, "2024-01-01T00:00:00Z", take_profit_order=True)

        mock_dependencies['balance_tracker'].sell_all.assert_called_once_with(2000)
        mock_dependencies['order_book'].add_order.assert_called_once()
        mock_dependencies['order_book'].add_order.call_args[0][0].order_type == OrderType.SELL
        mock_dependencies['order_book'].add_order.call_args[0][0].price == 2000

    def test_execute_stop_loss(self, order_manager, mock_dependencies):
        mock_dependencies['balance_tracker'].crypto_balance = 5

        order_manager.execute_take_profit_or_stop_loss_order(1500, "2024-01-01T00:00:00Z", stop_loss_order=True)

        mock_dependencies['balance_tracker'].sell_all.assert_called_once_with(1500)
        mock_dependencies['order_book'].add_order.assert_called_once()

    def test_process_buy_order_insufficient_balance(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['balance_tracker'].balance = 100
        mock_dependencies['transaction_validator'].validate_buy_order.side_effect = InsufficientBalanceError

        order_manager._process_buy_order(grid_level, 1000, "2024-01-01T00:00:00Z")

        mock_dependencies['balance_tracker'].update_after_buy.assert_not_called()

    def test_process_sell_order_insufficient_crypto(self, order_manager, mock_dependencies):
        grid_level = Mock()
        buy_grid_level = Mock()
        mock_dependencies['grid_manager'].find_lowest_completed_buy_grid.return_value = buy_grid_level
        mock_dependencies['transaction_validator'].validate_sell_order.side_effect = InsufficientCryptoBalanceError

        order_manager._process_sell_order(grid_level, 1000, "2024-01-01T00:00:00Z")

        mock_dependencies['balance_tracker'].update_after_sell.assert_not_called()

    def test_process_buy_order_grid_level_not_ready(self, order_manager, mock_dependencies):
        grid_level = Mock()
        grid_level.can_place_buy_order.return_value = False

        with pytest.raises(GridLevelNotReadyError):
            order_manager._place_order(grid_level, OrderType.BUY, 1000, 5, "2024-01-01T00:00:00Z")

    def test_multiple_buy_orders_for_sell(self, order_manager, mock_dependencies):
        grid_level = Mock()
        buy_order_1 = Mock(quantity=2)
        buy_order_2 = Mock(quantity=3)
        mock_dependencies['balance_tracker'].crypto_balance = 5

        
        mock_dependencies['grid_manager'].find_lowest_completed_buy_grid.return_value = Mock(buy_orders=[buy_order_1, buy_order_2])
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        
        order_manager.execute_order(OrderType.SELL, 1000, 1100, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_sell_order.assert_called_once_with(
            mock_dependencies['balance_tracker'].crypto_balance, 3, grid_level
        )
    
    def test_zero_quantity_order(self, order_manager, mock_dependencies):
        mock_dependencies['balance_tracker'].balance = 0
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = 1000
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        
        order_manager.execute_order(OrderType.BUY, 1000, 900, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_buy_order.assert_not_called()
        mock_dependencies['balance_tracker'].update_after_buy.assert_not_called()
    
    def test_extreme_price_fluctuation(self, order_manager, mock_dependencies):
        grid_level = Mock()

        mock_dependencies['grid_manager'].detect_grid_level_crossing.side_effect = [None, 5000]
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level

        order_manager.execute_order(OrderType.BUY, 5000, 1000, "2024-01-01T00:00:00Z")

        mock_dependencies['grid_manager'].detect_grid_level_crossing.assert_called_once_with(5000, 1000, sell=False)
        mock_dependencies['grid_manager'].get_grid_level.assert_not_called()  # No grid crossing, so no grid level

        # Reset mock call tracking for the second execution
        mock_dependencies['grid_manager'].detect_grid_level_crossing.reset_mock()

        order_manager.execute_order(OrderType.BUY, 5000, 4000, "2024-01-01T00:01:00Z")
        mock_dependencies['grid_manager'].detect_grid_level_crossing.assert_called_once_with(5000, 4000, sell=False)
        mock_dependencies['grid_manager'].get_grid_level.assert_called_once_with(5000)

    def test_negative_price_handling(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = None

        # Simulate a negative price scenario
        order_manager.execute_order(OrderType.BUY, -1000, 1000, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_buy_order.assert_not_called()
        mock_dependencies['balance_tracker'].update_after_buy.assert_not_called()

    def test_partial_crypto_balance_for_sell(self, order_manager, mock_dependencies):
        grid_level = Mock()
        buy_order = Mock(quantity=5)
        mock_dependencies['grid_manager'].find_lowest_completed_buy_grid.return_value = Mock(buy_orders=[buy_order])
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        mock_dependencies['balance_tracker'].crypto_balance = 3  # Partial balance available

        order_manager.execute_order(OrderType.SELL, 1000, 1100, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_sell_order.assert_called_once_with(3, buy_order.quantity, grid_level)
        mock_dependencies['balance_tracker'].update_after_sell.assert_called_once_with(3, 1000)
    
    def test_minimal_price_difference(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = None

        # Test minimal price difference (e.g., only $1 difference)
        order_manager.execute_order(OrderType.BUY, 1000, 999, "2024-01-01T00:00:00Z")
        
        mock_dependencies['grid_manager'].get_grid_level.assert_not_called()
        mock_dependencies['transaction_validator'].validate_buy_order.assert_not_called()
    
    def test_high_volume_trades(self, order_manager, mock_dependencies):
        grid_level = Mock()
        mock_dependencies['grid_manager'].detect_grid_level_crossing.return_value = 1000
        mock_dependencies['grid_manager'].get_grid_level.return_value = grid_level
        mock_dependencies['grid_manager'].get_order_size_per_grid.return_value = 10000
        mock_dependencies['balance_tracker'].balance = 1000000  # Large balance for a large trade
        
        order_manager.execute_order(OrderType.BUY, 1000, 900, "2024-01-01T00:00:00Z")
        
        mock_dependencies['transaction_validator'].validate_buy_order.assert_called_once()
        mock_dependencies['balance_tracker'].update_after_buy.assert_called_once()