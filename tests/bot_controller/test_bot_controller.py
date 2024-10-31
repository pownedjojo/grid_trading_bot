import pytest, asyncio
from unittest.mock import Mock, patch, AsyncMock
from core.bot_controller.bot_controller import BotController
from strategies.grid_trading_strategy import GridTradingStrategy
from core.order_handling.balance_tracker import BalanceTracker
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from core.bot_controller.exceptions import CommandParsingError, BalanceRetrievalError, OrderRetrievalError, StrategyControlError

class TestBotController:
    @pytest.fixture
    def setup_controller(self):
        strategy = AsyncMock(spec=GridTradingStrategy)
        balance_tracker = Mock(spec=BalanceTracker)
        trading_performance_analyzer = Mock(spec=TradingPerformanceAnalyzer)
        return BotController(strategy, balance_tracker, trading_performance_analyzer)

    @pytest.mark.asyncio
    async def test_command_listener_quit(self, setup_controller):
        controller = setup_controller
        with patch("builtins.input", side_effect=["quit"]):
            with patch.object(controller, "stop_listener", AsyncMock()) as mock_stop_listener:
                await controller.command_listener()
                mock_stop_listener.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_quit(self, setup_controller):
        controller = setup_controller
        with patch.object(controller, "_shutdown_bot", AsyncMock()) as mock_shutdown:
            await controller._handle_command("quit")
            mock_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_orders(self, setup_controller):
        controller = setup_controller
        controller.trading_performance_analyzer.get_formatted_orders.return_value = [
            ["BUY", "3000", "1", "2024-01-01T00:00:00Z", "100", "0.1"]
        ]
        with patch("tabulate.tabulate", return_value="Mocked Table") as mock_tabulate:
            await controller._handle_command("orders")
            controller.trading_performance_analyzer.get_formatted_orders.assert_called_once()
            mock_tabulate.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_balance(self, setup_controller):
        controller = setup_controller
        controller.balance_tracker.balance = 5000
        controller.balance_tracker.crypto_balance = 2
        with patch.object(controller.logger, "info") as mock_logger:
            await controller._handle_command("balance")
            mock_logger.assert_any_call("Current Fiat balance: 5000")
            mock_logger.assert_any_call("Current Crypto balance: 2")

    @pytest.mark.asyncio
    async def test_handle_command_stop(self, setup_controller):
        controller = setup_controller
        with patch.object(controller.strategy, "stop", AsyncMock()) as mock_stop:
            await controller._handle_command("stop")
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_restart(self, setup_controller):
        controller = setup_controller
        with patch.object(controller.strategy, "restart", AsyncMock()) as mock_restart:
            await controller._handle_command("restart")
            mock_restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_pause(self, setup_controller):
        controller = setup_controller
        with patch.object(controller.strategy, "stop", AsyncMock()) as mock_stop, patch.object(controller.strategy, "restart", AsyncMock()) as mock_restart, patch("asyncio.sleep", AsyncMock()):
            await controller._handle_command("pause 5")
            mock_stop.assert_called_once()
            mock_restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_pause_invalid_duration(self, setup_controller):
        controller = setup_controller
        with pytest.raises(CommandParsingError, match="Invalid pause duration."):
            await controller._handle_command("pause abc")

    @pytest.mark.asyncio
    async def test_handle_command_unknown(self, setup_controller):
        controller = setup_controller
        with pytest.raises(CommandParsingError, match="Unknown command"):
            await controller._handle_command("unknown_command")

    @pytest.mark.asyncio
    async def test_display_orders_exception(self, setup_controller):
        controller = setup_controller
        controller.trading_performance_analyzer.get_formatted_orders.side_effect = Exception("Order fetch error")
        with pytest.raises(OrderRetrievalError, match="Error retrieving orders: Order fetch error"):
            await controller._display_orders()

    @pytest.mark.asyncio
    async def test_display_balance_exception(self, setup_controller):
        controller = setup_controller
        controller.balance_tracker.balance = None  # Simulate balance retrieval failure
        with pytest.raises(BalanceRetrievalError, match="Error retrieving balance"):
            await controller._display_balance()

    @pytest.mark.asyncio
    async def test_shutdown_bot_exception(self, setup_controller):
        controller = setup_controller
        controller.strategy.stop.side_effect = Exception("Stop error")
        with pytest.raises(StrategyControlError, match="Error stopping the bot: Stop error"):
            await controller._shutdown_bot()

    @pytest.mark.asyncio
    async def test_stop_strategy_exception(self, setup_controller):
        controller = setup_controller
        controller.strategy.stop.side_effect = Exception("Stop error")
        with pytest.raises(StrategyControlError, match="Error stopping the strategy: Stop error"):
            await controller._stop_strategy()

    @pytest.mark.asyncio
    async def test_restart_strategy_exception(self, setup_controller):
        controller = setup_controller
        controller.strategy.restart.side_effect = Exception("Restart error")
        with pytest.raises(StrategyControlError, match="Error restarting the strategy: Restart error"):
            await controller._restart_strategy()