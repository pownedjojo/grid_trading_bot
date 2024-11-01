import pytest, asyncio
from unittest.mock import Mock, patch, AsyncMock
from core.bot_controller.bot_controller import BotController
from strategies.grid_trading_strategy import GridTradingStrategy
from core.order_handling.balance_tracker import BalanceTracker
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from core.bot_controller.exceptions import CommandParsingError, BalanceRetrievalError, OrderRetrievalError, StrategyControlError

@pytest.mark.asyncio
class TestBotController:
    @pytest.fixture
    def setup_bot_controller(self):
        strategy = Mock(spec=GridTradingStrategy)
        balance_tracker = Mock(spec=BalanceTracker)
        trading_performance_analyzer = Mock(spec=TradingPerformanceAnalyzer)
        bot_controller = BotController(strategy, balance_tracker, trading_performance_analyzer)
        return bot_controller, strategy, balance_tracker, trading_performance_analyzer

    @patch("builtins.input", side_effect=["quit"])
    async def test_command_listener_quit(self, mock_input, setup_bot_controller):
        bot_controller, strategy, _, _ = setup_bot_controller
        strategy.stop = AsyncMock()

        await bot_controller.command_listener()

        strategy.stop.assert_called_once()
        assert bot_controller._stop_listener

    @patch("builtins.input", side_effect=["balance", "quit"])
    async def test_command_listener_balance_positive(self, mock_input, setup_bot_controller):
        bot_controller, _, balance_tracker, _ = setup_bot_controller
        balance_tracker.balance = 1000.0
        balance_tracker.crypto_balance = 2.0

        await bot_controller.command_listener()

        assert balance_tracker.balance == 1000.0
        assert balance_tracker.crypto_balance == 2.0

    @patch("builtins.input", side_effect=["balance", "quit"])
    async def test_command_listener_balance_zero_negative(self, mock_input, setup_bot_controller):
        bot_controller, _, balance_tracker, _ = setup_bot_controller
        balance_tracker.balance = 0.0
        balance_tracker.crypto_balance = -0.5

        await bot_controller.command_listener()

        assert balance_tracker.balance == 0.0
        assert balance_tracker.crypto_balance == -0.5

    @patch("builtins.input", side_effect=["orders", "quit"])
    async def test_command_listener_orders_with_orders(self, mock_input, setup_bot_controller):
        bot_controller, _, _, trading_performance_analyzer = setup_bot_controller
        trading_performance_analyzer.get_formatted_orders = Mock(return_value=[
            {"Order Type": "BUY", "Price": 1000, "Quantity": 0.1, "Timestamp": "2024-01-01T00:00:00Z"}
        ])

        await bot_controller.command_listener()

        trading_performance_analyzer.get_formatted_orders.assert_called_once()

    @patch("builtins.input", side_effect=["orders", "quit"])
    async def test_command_listener_orders_empty(self, mock_input, setup_bot_controller):
        bot_controller, _, _, trading_performance_analyzer = setup_bot_controller
        trading_performance_analyzer.get_formatted_orders = Mock(return_value=[])

        await bot_controller.command_listener()

        trading_performance_analyzer.get_formatted_orders.assert_called_once()

    @patch("builtins.input", side_effect=["restart", "quit"])
    async def test_command_listener_restart(self, mock_input, setup_bot_controller):
        bot_controller, strategy, _, _ = setup_bot_controller
        strategy.restart = AsyncMock()

        await bot_controller.command_listener()

        strategy.restart.assert_called_once()

    @patch("builtins.input", side_effect=["pause 2", "quit"])
    @patch("asyncio.sleep", new_callable=AsyncMock)  # Patch asyncio.sleep to skip actual delay
    async def test_command_listener_pause_valid(self, mock_sleep, mock_input, setup_bot_controller):
        bot_controller, strategy, _, _ = setup_bot_controller
        strategy.stop = AsyncMock()
        strategy.restart = AsyncMock()

        await bot_controller.command_listener()

        assert strategy.stop.call_count >= 1, "Expected 'stop' to be called at least once during pause"
        mock_sleep.assert_awaited_once_with(2)  # Ensure sleep was called with the correct duration
        strategy.restart.assert_called_once_with()

    @patch("builtins.input", side_effect=["unknown", "quit"])
    @patch("core.bot_controller.bot_controller.logging.Logger.warning")
    async def test_command_listener_unknown_command(self, mock_log_warning, mock_input, setup_bot_controller):
        bot_controller, _, _, _ = setup_bot_controller

        await bot_controller.command_listener()

        mock_log_warning.assert_any_call('Command error: Unknown command: unknown')
    
    @patch("builtins.input", side_effect=["orders", "quit"])
    async def test_handle_command_order_retrieval_error(self, mock_input, setup_bot_controller):
        bot_controller, _, _, trading_performance_analyzer = setup_bot_controller
        trading_performance_analyzer.get_formatted_orders.side_effect = Exception("Order error")
        
        with pytest.raises(OrderRetrievalError):
            await bot_controller._display_orders()
    
    @patch("builtins.input", side_effect=["balance", "quit"])
    async def test_handle_command_balance_retrieval_error(self, mock_input, setup_bot_controller):
        bot_controller, _, balance_tracker, _ = setup_bot_controller
        balance_tracker.balance = None  # Simulate error condition for balance retrieval
        
        with pytest.raises(BalanceRetrievalError):
            await bot_controller._display_balance()