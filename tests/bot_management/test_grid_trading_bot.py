import pytest, os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from config.config_manager import ConfigManager
from core.bot_management.grid_trading_bot import GridTradingBot
from core.bot_management.notification.notification_handler import NotificationHandler
from core.services.exceptions import UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError
from config.trading_mode import TradingMode

@patch.dict(os.environ, {"EXCHANGE_API_KEY": "test_api_key", "EXCHANGE_SECRET_KEY": "test_secret_key"})
class TestGridTradingBot:
    @pytest.fixture
    def config_manager(self):
        mock_config = Mock(spec=ConfigManager)
        mock_config.get_trading_mode.return_value = TradingMode.LIVE
        mock_config.get_initial_balance.return_value = 1000
        mock_config.get_exchange_name.return_value = "binance"
        mock_config.get_grid_type.return_value = "arithmetic"
        mock_config.get_top_range.return_value = 2000
        mock_config.get_bottom_range.return_value = 1500
        mock_config.get_num_grids.return_value = 10
        return mock_config

    @pytest.fixture
    def notification_handler(self):
        return Mock(spec=NotificationHandler)

    @pytest.fixture
    def bot(self, config_manager, notification_handler):
        return GridTradingBot(
            config_path="config.json",
            config_manager=config_manager,
            notification_handler=notification_handler,
            save_performance_results_path="results.json",
            no_plot=True
        )

    @patch("core.bot_management.grid_trading_bot.ExchangeServiceFactory.create_exchange_service", side_effect=UnsupportedExchangeError("Unsupported Exchange"))
    def test_initialization_with_unsupported_exchange_error(self, mock_exchange_service, config_manager, notification_handler):
        # Expect exit due to unsupported exchange error
        with pytest.raises(SystemExit):
            GridTradingBot("config.json", config_manager, notification_handler)

    @patch("core.bot_management.grid_trading_bot.ExchangeServiceFactory.create_exchange_service", side_effect=DataFetchError("Data Fetch Error"))
    def test_initialization_with_data_fetch_error(self, mock_exchange_service, config_manager, notification_handler):
        with pytest.raises(SystemExit):
            GridTradingBot("config.json", config_manager, notification_handler)

    @patch("core.bot_management.grid_trading_bot.ExchangeServiceFactory.create_exchange_service", side_effect=UnsupportedTimeframeError("Unsupported Timeframe"))
    def test_initialization_with_unsupported_timeframe_error(self, mock_exchange_service, config_manager, notification_handler):
        with pytest.raises(SystemExit):
            GridTradingBot("config.json", config_manager, notification_handler)

    @patch("core.bot_management.grid_trading_bot.ExchangeServiceFactory.create_exchange_service")
    @pytest.mark.asyncio
    async def test_is_healthy(self, mock_exchange_service, bot):
        bot.strategy = Mock()
        bot.strategy._running = True
        bot.exchange_service.get_exchange_status = AsyncMock(return_value={"status": "ok"})

        health_status = await bot.get_bot_health_status()

        assert health_status["strategy"] is True
        assert health_status["exchange_status"] == "ok"
        assert health_status["overall"] is True

    @pytest.mark.asyncio
    async def test_is_healthy_strategy_stopped(self, bot):
        bot.strategy = Mock()
        bot.strategy._running = False
        bot.exchange_service.get_exchange_status = AsyncMock(return_value={"status": "ok"})

        health_status = await bot.get_bot_health_status()

        assert health_status["strategy"] is False
        assert health_status["exchange_status"] == "ok"
        assert health_status["overall"] is False

    @patch("core.bot_management.grid_trading_bot.GridTradingBot._generate_and_log_performance")
    @pytest.mark.asyncio
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

    @patch("core.bot_management.grid_trading_bot.GridTradingStrategy", new_callable=MagicMock)
    @pytest.mark.asyncio
    async def test_check_strategy_health(self, mock_strategy, bot):
        bot.strategy = mock_strategy

        mock_strategy._running = True
        result = await bot._check_strategy_health()
        assert result is True

        mock_strategy._running = False
        result = await bot._check_strategy_health()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_exchange_status(self, bot):
        bot.exchange_service = MagicMock()
        bot.exchange_service.get_exchange_status = AsyncMock(return_value={"status": "ok"})

        result = await bot._get_exchange_status()
        assert result == "ok"