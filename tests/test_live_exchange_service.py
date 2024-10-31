import pytest, ccxt
from unittest.mock import Mock, patch, AsyncMock
from core.services.live_exchange_service import LiveExchangeService
from core.services.exceptions import UnsupportedExchangeError, MissingEnvironmentVariableError, DataFetchError, OrderCancellationError, InvalidOrderTypeError
from config.config_manager import ConfigManager
from config.trading_mode import TradingMode

class TestLiveExchangeService:
    @pytest.fixture
    def config_manager(self):
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_exchange_name.return_value = "binance"
        config_manager.get_trading_mode.return_value = TradingMode.LIVE
        return config_manager

    @pytest.fixture
    def mock_exchange_instance(self):
        exchange = AsyncMock()
        exchange.create_limit_buy_order.return_value = {"status": "filled"}
        exchange.create_limit_sell_order.return_value = {"status": "filled"}
        exchange.fetch_balance.return_value = {"total": {"USD": 1000}}
        exchange.fetch_ticker.return_value = {"last": 50000.0}
        exchange.fetch_order.return_value = {"status": "closed"}
        exchange.cancel_order.return_value = {"status": "canceled"}
        return exchange

    @pytest.fixture
    def setup_env_vars(self, monkeypatch):
        monkeypatch.setenv("EXCHANGE_API_KEY", "test_api_key")
        monkeypatch.setenv("EXCHANGE_SECRET_KEY", "test_secret_key")

    @patch("core.services.live_exchange_service.ccxt")
    @patch("core.services.live_exchange_service.getattr")
    def test_initialization_with_env_vars(self, mock_getattr, mock_ccxt, config_manager, setup_env_vars):
        mock_exchange_instance = Mock()
        mock_ccxt.binance.return_value = mock_exchange_instance
        mock_getattr.return_value = mock_ccxt.binance

        service = LiveExchangeService(config_manager, is_paper_trading_activated=False)
        assert isinstance(service, LiveExchangeService)
        assert service.exchange_name == "binance"
        assert service.api_key == "test_api_key"
        assert service.secret_key == "test_secret_key"
        assert service.exchange == mock_exchange_instance
        assert service.exchange.enableRateLimit, "Expected rate limiting to be enabled for live mode"

    @patch("core.services.live_exchange_service.getattr")
    def test_missing_secret_key_raises_error(self, mock_getattr, config_manager, monkeypatch):
        monkeypatch.delenv("EXCHANGE_SECRET_KEY", raising=False)
        monkeypatch.setenv("EXCHANGE_API_KEY", "test_api_key")

        with pytest.raises(MissingEnvironmentVariableError, match="Missing required environment variable: EXCHANGE_SECRET_KEY"):
            LiveExchangeService(config_manager, is_paper_trading_activated=False)

    @patch("core.services.live_exchange_service.getattr")
    def test_missing_api_key_raises_error(self, mock_getattr, config_manager, monkeypatch):
        monkeypatch.delenv("EXCHANGE_API_KEY", raising=False)
        monkeypatch.setenv("EXCHANGE_SECRET_KEY", "test_secret_key")

        with pytest.raises(MissingEnvironmentVariableError, match="Missing required environment variable: EXCHANGE_API_KEY"):
            LiveExchangeService(config_manager, is_paper_trading_activated=False)

    @patch("core.services.live_exchange_service.ccxt")
    @patch("core.services.live_exchange_service.getattr")
    def test_sandbox_mode_initialization(self, mock_getattr, mock_ccxt, config_manager, setup_env_vars):
        config_manager.get_trading_mode.return_value = TradingMode.PAPER_TRADING

        mock_exchange_instance = Mock()
        mock_ccxt.binance.return_value = mock_exchange_instance
        mock_getattr.return_value = mock_ccxt.binance

        service = LiveExchangeService(config_manager, is_paper_trading_activated=True)
        assert service.is_paper_trading_activated is True
        mock_exchange_instance.set_sandbox_mode.assert_called_once_with(True)

    @patch("core.services.live_exchange_service.getattr")
    def test_unsupported_exchange_raises_error(self, mock_getattr, config_manager, setup_env_vars):
        config_manager.get_exchange_name.return_value = "unsupported_exchange"
        mock_getattr.side_effect = AttributeError

        with pytest.raises(UnsupportedExchangeError, match="The exchange 'unsupported_exchange' is not supported."):
            LiveExchangeService(config_manager, is_paper_trading_activated=False)

    @patch("core.services.live_exchange_service.ccxt")
    @patch("core.services.live_exchange_service.getattr")
    @pytest.mark.asyncio
    async def test_place_order_successful(self, mock_getattr, mock_ccxt, config_manager, setup_env_vars, mock_exchange_instance):
        mock_getattr.return_value = mock_ccxt.binance
        mock_ccxt.binance.return_value = mock_exchange_instance

        service = LiveExchangeService(config_manager, is_paper_trading_activated=False)
        result = await service.place_order("BTC/USD", "buy", 1, 50000.0)

        assert result["status"] == "filled"
        mock_exchange_instance.create_limit_buy_order.assert_called_once_with("BTC/USD", 1, 50000.0)

    @patch("core.services.live_exchange_service.getattr")
    @pytest.mark.asyncio
    async def test_place_order_invalid_type_raises_error(self, mock_getattr, config_manager, setup_env_vars):
        mock_exchange_instance = AsyncMock()
        mock_getattr.return_value = mock_exchange_instance

        service = LiveExchangeService(config_manager, is_paper_trading_activated=False)

        with pytest.raises(InvalidOrderTypeError, match="Error placing order: Invalid order type specified"):
            await service.place_order("BTC/USD", "invalid_type", 1, 50000.0)

    @patch("core.services.live_exchange_service.getattr")
    @pytest.mark.asyncio
    async def test_place_order_unexpected_error(self, mock_getattr, config_manager, setup_env_vars):
        mock_exchange_instance = AsyncMock()
        mock_exchange_instance.create_limit_buy_order.side_effect = Exception("Unexpected error")
        mock_getattr.return_value = mock_exchange_instance

        service = LiveExchangeService(config_manager, is_paper_trading_activated=False)

        with pytest.raises(DataFetchError, match="Unexpected error placing order"):
            await service.place_order("BTC/USD", "buy", 1, 50000.0)

    @patch("core.services.live_exchange_service.ccxt")
    @patch("core.services.live_exchange_service.getattr")
    @pytest.mark.asyncio
    async def test_get_current_price_successful(self, mock_getattr, mock_ccxt, config_manager, setup_env_vars, mock_exchange_instance):
        mock_getattr.return_value = mock_ccxt.binance
        mock_ccxt.binance.return_value = mock_exchange_instance

        service = LiveExchangeService(config_manager, is_paper_trading_activated=False)
        result = await service.get_current_price("BTC/USD")

        assert result == 50000.0
        mock_exchange_instance.fetch_ticker.assert_called_once_with("BTC/USD")

    @patch("core.services.live_exchange_service.ccxt")
    @patch("core.services.live_exchange_service.getattr")
    @pytest.mark.asyncio
    async def test_cancel_order_successful(self, mock_getattr, mock_ccxt, config_manager, setup_env_vars, mock_exchange_instance):
        mock_getattr.return_value = mock_ccxt.binance
        mock_ccxt.binance.return_value = mock_exchange_instance

        service = LiveExchangeService(config_manager, is_paper_trading_activated=False)
        result = await service.cancel_order("order123", "BTC/USD")

        assert result["status"] == "canceled"
        mock_exchange_instance.cancel_order.assert_called_once_with("order123", "BTC/USD")
    
    @patch("core.services.live_exchange_service.getattr")
    @patch("core.services.live_exchange_service.ccxt")
    def test_fetch_ohlcv_not_implemented(self, mock_ccxt, mock_getattr, setup_env_vars, config_manager):
        mock_exchange_instance = Mock()
        mock_ccxt.binance.return_value = mock_exchange_instance
        mock_getattr.return_value = mock_ccxt.binance

        # Instantiate the LiveExchangeService
        service = LiveExchangeService(config_manager, is_paper_trading_activated=False)

        # Assert NotImplementedError is raised for fetch_ohlcv
        with pytest.raises(NotImplementedError, match="fetch_ohlcv is not used in live or paper trading mode."):
            service.fetch_ohlcv("BTC/USD", "1m", "start_date", "end_date")