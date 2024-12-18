import pytest
from unittest.mock import Mock, patch, AsyncMock
from core.bot_management.event_bus import EventBus, Events
from core.bot_management.grid_trading_bot import GridTradingBot
from core.bot_management.bot_controller.bot_controller import BotController
from core.order_handling.balance_tracker import BalanceTracker
from strategies.grid_trading_strategy import GridTradingStrategy

@pytest.mark.asyncio
class TestBotController:
    @pytest.fixture
    def setup_bot_controller(self):
        bot = Mock(spec=GridTradingBot)
        bot.strategy = Mock(spec=GridTradingStrategy)
        bot.strategy.get_formatted_orders = Mock(return_value=[])
        bot.balance_tracker = Mock(spec=BalanceTracker)
        bot.balance_tracker.balance = 1000.0
        bot.balance_tracker.crypto_balance = 2.0
        bot.logger = Mock()
        event_bus = Mock(spec=EventBus)
        bot_controller = BotController(bot, event_bus)
        return bot_controller, bot, event_bus

    @patch("builtins.input", side_effect=["quit"])
    async def test_command_listener_quit(self, mock_input, setup_bot_controller):
        bot_controller, _, event_bus = setup_bot_controller
        event_bus.publish_sync = Mock()

        await bot_controller.command_listener()

        event_bus.publish_sync.assert_called_once_with(Events.STOP_BOT, "User requested shutdown")
        assert bot_controller._stop_listening

    @patch("builtins.input", side_effect=["balance", "quit"])
    async def test_command_listener_balance_positive(self, mock_input, setup_bot_controller):
        bot_controller, bot, _ = setup_bot_controller
        bot.balance_tracker = Mock()
        bot.balance_tracker.balance = 1000.0
        bot.balance_tracker.reserved_fiat = 200.0
        bot.balance_tracker.crypto_balance = 2.0
        bot.balance_tracker.reserved_crypto = 0.5
        bot_controller.logger = Mock()
        bot.get_balances = Mock(return_value={
            "fiat": bot.balance_tracker.balance,
            "reserved_fiat": bot.balance_tracker.reserved_fiat,
            "crypto": bot.balance_tracker.crypto_balance,
            "reserved_crypto": bot.balance_tracker.reserved_crypto,
        })

        await bot_controller.command_listener()

        bot.get_balances.assert_called_once()
        bot_controller.logger.info.assert_any_call(f"Current balances: {bot.get_balances.return_value}")

    @patch("builtins.input", side_effect=["balance", "quit"])
    async def test_command_listener_balance_zero_negative(self, mock_input, setup_bot_controller):
        bot_controller, bot, _ = setup_bot_controller
        bot.balance_tracker.balance = 0.0
        bot.balance_tracker.crypto_balance = -0.5
        bot.balance_tracker.reserved_fiat = 0.0
        bot.balance_tracker.reserved_crypto = 0.0
        bot.get_balances = Mock(return_value={
            "fiat": bot.balance_tracker.balance,
            "reserved_fiat": bot.balance_tracker.reserved_fiat,
            "crypto": bot.balance_tracker.crypto_balance,
            "reserved_crypto": bot.balance_tracker.reserved_crypto,
        })
        bot_controller.logger = Mock()

        await bot_controller.command_listener()

        bot.get_balances.assert_called_once()
        bot_controller.logger.info.assert_any_call(f"Current balances: {bot.get_balances.return_value}")

    @patch("builtins.input", side_effect=["orders", "quit"])
    async def test_command_listener_orders_with_orders(self, mock_input, setup_bot_controller):
        bot_controller, bot, _ = setup_bot_controller
        bot.strategy.get_formatted_orders = Mock(return_value=[
            ["BUY", "LIMIT", 1000, 0.1, "2024-01-01T00:00:00Z", "Level 1", "0.1%"]
        ])
        bot_controller.logger = Mock()

        await bot_controller.command_listener()

        bot.strategy.get_formatted_orders.assert_called_once()

    @patch("builtins.input", side_effect=["orders", "quit"])
    async def test_command_listener_orders_empty(self, mock_input, setup_bot_controller):
        bot_controller, bot, _ = setup_bot_controller
        bot.strategy.get_formatted_orders = Mock(return_value=[])
        bot_controller.logger = Mock()

        await bot_controller.command_listener()

        bot.strategy.get_formatted_orders.assert_called_once()

    @patch("builtins.input", side_effect=["restart", "quit"])
    async def test_command_listener_restart(self, mock_input, setup_bot_controller):
        bot_controller, bot, event_bus = setup_bot_controller
        bot.restart = AsyncMock()

        # Mock the event bus to simulate the behavior of triggering bot restart
        async def mock_publish(event, reason):
            if event == Events.START_BOT:
                await bot.restart()

        event_bus.publish = AsyncMock(side_effect=mock_publish)

        await bot_controller.command_listener()

        bot.restart.assert_called_once()
        event_bus.publish.assert_any_call(Events.STOP_BOT, "User issued restart command")
        event_bus.publish.assert_any_call(Events.START_BOT, "User issued restart command")

    @patch("builtins.input", side_effect=["pause 2", "quit"])
    @patch("asyncio.sleep", new_callable=AsyncMock)  # Patch asyncio.sleep to skip actual delay
    async def test_command_listener_pause_valid(self, mock_sleep, mock_input, setup_bot_controller):
        bot_controller, bot, event_bus = setup_bot_controller
        bot.stop = AsyncMock()
        bot.restart = AsyncMock()

        # Mock the event bus to simulate bot stop and restart
        async def mock_publish(event, reason):
            if event == Events.STOP_BOT:
                await bot.stop()
            elif event == Events.START_BOT:
                await bot.restart()

        event_bus.publish = AsyncMock(side_effect=mock_publish)

        await bot_controller.command_listener()

        assert bot.stop.call_count == 1, "Expected 'stop' to be called once during pause"
        mock_sleep.assert_awaited_once_with(2)  # Ensure sleep was called with the correct duration
        bot.restart.assert_called_once()

    @patch("builtins.input", side_effect=["unknown", "quit"])
    @patch("core.bot_management.bot_controller.bot_controller.logging.Logger.warning")
    async def test_command_listener_unknown_command(self, mock_log_warning, mock_input, setup_bot_controller):
        bot_controller, _, _ = setup_bot_controller

        await bot_controller.command_listener()

        mock_log_warning.assert_any_call("Command error: Unknown command: unknown")