import unittest
import pytest, os, logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock, ANY
from config.config_manager import ConfigManager
from core.bot_management.grid_trading_bot import GridTradingBot
from core.bot_management.event_bus import EventBus, Events
from core.bot_management.notification.notification_handler import NotificationHandler
from core.services.exceptions import UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError
from config.trading_mode import TradingMode

@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {"EXCHANGE_API_KEY": "test_api_key", "EXCHANGE_SECRET_KEY": "test_secret_key"}):
        yield

@pytest.mark.asyncio
class TestGridTradingBot:
    @pytest.fixture
    def config_manager(self):
        mock_config = Mock(spec=ConfigManager)
        mock_config.get_trading_mode.return_value = TradingMode.LIVE
        mock_config.get_initial_balance.return_value = 1000
        mock_config.get_exchange_name.return_value = "binance"
        mock_config.get_spacing_type.return_value = "arithmetic"
        mock_config.get_top_range.return_value = 2000
        mock_config.get_bottom_range.return_value = 1500
        mock_config.get_num_grids.return_value = 10
        return mock_config

    @pytest.fixture
    def mock_event_bus(self):
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = Mock()
        event_bus.publish_sync = Mock()
        return event_bus

    @pytest.fixture
    def notification_handler(self):
        return Mock(spec=NotificationHandler)

    @pytest.fixture
    def bot(self, config_manager, notification_handler, mock_event_bus):
        return GridTradingBot(
            config_path="config.json",
            config_manager=config_manager,
            notification_handler=notification_handler,
            event_bus=mock_event_bus,
            save_performance_results_path="results.json",
            no_plot=True
        )

    @patch("core.bot_management.grid_trading_bot.ExchangeServiceFactory.create_exchange_service", side_effect=UnsupportedExchangeError("Unsupported Exchange"))
    def test_initialization_with_unsupported_exchange_error(self, mock_exchange_service, config_manager, notification_handler, mock_event_bus):
        mock_event_bus.subscribe = Mock()

        with pytest.raises(SystemExit):
            GridTradingBot("config.json", config_manager, notification_handler, mock_event_bus)

        bot_logger = logging.getLogger("GridTradingBot")
        with patch.object(bot_logger, "error") as mock_logger_error:
            with pytest.raises(SystemExit):
                GridTradingBot("config.json", config_manager, notification_handler, mock_event_bus)

            mock_logger_error.assert_called_once_with("UnsupportedExchangeError: Unsupported Exchange")

    @patch("core.bot_management.grid_trading_bot.ExchangeServiceFactory.create_exchange_service", side_effect=DataFetchError("Data Fetch Error"))
    def test_initialization_with_data_fetch_error(self, mock_exchange_service, config_manager, notification_handler, mock_event_bus):
        with patch("core.bot_management.grid_trading_bot.logging.getLogger") as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance

            with pytest.raises(SystemExit):
                GridTradingBot("config.json", config_manager, notification_handler, mock_event_bus)

            logger_instance.error.assert_called_once_with("DataFetchError: Data Fetch Error")

    @patch("core.bot_management.grid_trading_bot.ExchangeServiceFactory.create_exchange_service", side_effect=UnsupportedTimeframeError("Unsupported Timeframe"))
    def test_initialization_with_unsupported_timeframe_error(self, mock_exchange_service, config_manager, notification_handler, mock_event_bus):
        with patch("core.bot_management.grid_trading_bot.logging.getLogger") as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance

            with pytest.raises(SystemExit):
                GridTradingBot("config.json", config_manager, notification_handler, mock_event_bus)

            logger_instance.error.assert_called_once_with("UnsupportedTimeframeError: Unsupported Timeframe")
    
    @patch("core.bot_management.grid_trading_bot.ExchangeServiceFactory.create_exchange_service", side_effect=Exception("Unexpected Error"))
    def test_initialization_with_unexpected_exception(self, mock_exchange_service, config_manager, notification_handler, mock_event_bus):
        with patch("core.bot_management.grid_trading_bot.logging.getLogger") as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance

            with pytest.raises(SystemExit):
                GridTradingBot("config.json", config_manager, notification_handler, mock_event_bus)

            logger_instance.error.assert_any_call("An unexpected error occurred.")
            logger_instance.error.assert_any_call(unittest.mock.ANY)
    
    def test_initialization_with_missing_config(self, notification_handler, mock_event_bus):
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_trading_mode.side_effect = AttributeError("Missing configuration")

        with patch("core.bot_management.grid_trading_bot.logging.getLogger") as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance

            with pytest.raises(SystemExit):
                GridTradingBot("config.json", config_manager, notification_handler, mock_event_bus)

            logger_instance.error.assert_any_call("An unexpected error occurred.")
            logger_instance.error.assert_any_call(unittest.mock.ANY)

    async def test_get_bot_health_status(self, bot):
        bot._check_strategy_health = AsyncMock(return_value=True)
        bot._get_exchange_status = AsyncMock(return_value="ok")

        health_status = await bot.get_bot_health_status()

        assert health_status["strategy"] is True
        assert health_status["exchange_status"] == "ok"
        assert health_status["overall"] is True

    async def test_is_healthy_strategy_stopped(self, bot):
        bot.strategy = Mock()
        bot.strategy._running = False
        bot.exchange_service.get_exchange_status = AsyncMock(return_value={"status": "ok"})

        health_status = await bot.get_bot_health_status()

        assert health_status["strategy"] is False
        assert health_status["exchange_status"] == "ok"
        assert health_status["overall"] is False

    @patch("core.bot_management.grid_trading_bot.GridTradingBot._generate_and_log_performance")
    async def test_generate_and_log_performance_direct(self, mock_performance, bot):
        mock_performance.return_value = {
            "config": bot.config_path,
            "performance_summary": {"profit": 100},
            "orders": []
        }

        result = bot._generate_and_log_performance()

        assert result == {
            "config": bot.config_path,
            "performance_summary": {"profit": 100},
            "orders": []
        }

    async def test_get_exchange_status(self, bot):
        bot.exchange_service = MagicMock()
        bot.exchange_service.get_exchange_status = AsyncMock(return_value={"status": "ok"})

        result = await bot._get_exchange_status()
        assert result == "ok"

    async def test_get_balance_zero_values(self, bot):
        bot.balance_tracker.balance = 0.0
        bot.balance_tracker.crypto_balance = 0.0

        result = await bot.get_balance()

        assert result == {"fiat": 0.0, "crypto": 0.0}
    
    @patch("core.bot_management.grid_trading_bot.GridTradingStrategy")
    async def test_run_with_exception(self, mock_strategy, bot):
        bot.order_status_tracker.start_tracking = Mock()
        bot.strategy.run = AsyncMock(side_effect=Exception("Test Exception"))
        mock_grid_manager = Mock()
        mock_grid_manager.initialize_grids_and_levels = Mock()
        bot.strategy.grid_manager = mock_grid_manager

        with patch.object(bot.logger, "error") as mock_logger_error:
            with pytest.raises(SystemExit):  # Ensure the bot exits on an unexpected exception
                await bot.run()
            
            mock_logger_error.assert_any_call("An unexpected error occurred Test Exception")

    @patch("core.bot_management.grid_trading_bot.OrderStatusTracker")
    async def test_stop_bot(self, mock_order_status_tracker, bot):
        bot.is_running = True
        bot.strategy.stop = AsyncMock()
        bot.order_status_tracker.stop_tracking = AsyncMock()

        await bot._stop()

        bot.strategy.stop.assert_awaited_once()
        bot.order_status_tracker.stop_tracking.assert_awaited_once()
        bot.event_bus.publish_sync.assert_called_once_with(Events.STOP_BOT, "Bot stopped")

    async def test_restart_bot(self, bot):
        bot.is_running = True
        bot.strategy.restart = AsyncMock()
        bot.order_status_tracker.start_tracking = Mock()
        bot._stop = AsyncMock()

        await bot.restart()

        bot._stop.assert_awaited_once()
        bot.strategy.restart.assert_awaited_once()
        bot.order_status_tracker.start_tracking.assert_called_once()

    async def test_restart_when_not_running(self, bot):
        bot.is_running = False
        bot._stop = AsyncMock()
        bot.strategy.restart = AsyncMock()
        bot.order_status_tracker.start_tracking = Mock()

        await bot.restart()

        bot._stop.assert_not_awaited()
        bot.strategy.restart.assert_awaited_once()
        bot.order_status_tracker.start_tracking.assert_called_once()
    
    async def test_handle_stop_bot_event(self, bot):
        bot.is_running = True
        bot._stop = AsyncMock()

        await bot._handle_stop_bot_event("Test reason")

        bot._stop.assert_awaited_once()

    async def test_handle_stop_bot_event_when_already_stopped(self, bot):
        bot.is_running = False
        bot._stop = AsyncMock()

        await bot._handle_stop_bot_event("Test reason")

        bot._stop.assert_not_awaited()

    async def test_handle_start_bot_event_when_already_running(self, bot):
        bot.is_running = True
        bot.restart = AsyncMock()

        await bot._handle_start_bot_event("Test reason")

        bot.restart.assert_not_awaited()

    async def test_handle_start_bot_event(self, bot):
        bot.is_running = False
        bot.restart = AsyncMock()

        await bot._handle_start_bot_event("Test reason")

        bot.restart.assert_awaited_once()
    
    @patch("core.bot_management.grid_trading_bot.GridTradingStrategy")
    async def test_run_with_plotting_enabled(self, mock_strategy, bot):
        bot.no_plot = False
        bot.strategy.plot_results = Mock()
        bot.strategy.run = AsyncMock()
        bot.order_status_tracker.start_tracking = Mock()
        mock_grid_manager = Mock()
        mock_grid_manager.initialize_grids_and_levels = Mock()
        bot.strategy.grid_manager = mock_grid_manager

        await bot.run()

        bot.strategy.plot_results.assert_called_once()
        bot.strategy.run.assert_awaited_once()
        bot.order_status_tracker.start_tracking.assert_called_once()