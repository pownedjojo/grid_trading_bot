import pytest
from unittest.mock import Mock, patch
import ccxt
import pandas as pd
from core.services.data_manager import DataManager
from core.services.exceptions import UnsupportedExchangeError, DataFetchError

class TestDataManager:
    @pytest.fixture
    def config_manager(self):
        mock_config = Mock()
        mock_config.get_exchange_name.return_value = "binance"
        return mock_config

    @pytest.fixture
    def data_manager(self, config_manager):
        return DataManager(config_manager)

    @pytest.fixture
    def mock_exchange(self):
        mock_exchange = Mock()
        mock_exchange.parse8601.side_effect = lambda x: pd.Timestamp(x).value // 10**6
        return mock_exchange

    @patch("core.services.data_manager.ccxt.binance")
    def test_initialization_supported_exchange(self, mock_ccxt, config_manager):
        data_manager = DataManager(config_manager)
        mock_ccxt.assert_called_once()

    def test_initialization_unsupported_exchange(self, config_manager):
        config_manager.get_exchange_name.return_value = "unsupported_exchange"
        with pytest.raises(UnsupportedExchangeError):
            DataManager(config_manager)

    @patch("core.services.data_manager.ccxt.binance")
    def test_fetch_ohlcv_success(self, mock_ccxt, config_manager):
        mock_exchange = mock_ccxt.return_value
        mock_exchange.fetch_ohlcv.return_value = [
            [1622505600000, 34000, 35000, 33000, 34500, 1000],  # June 1, 2021
            [1622592000000, 34500, 35500, 34000, 35000, 1200]   # June 2, 2021
        ]
        mock_exchange.parse8601.side_effect = [
            1622505600000,  # start_date in milliseconds
            1622592000000   # end_date in milliseconds
        ]

        data_manager = DataManager(config_manager)
        pair = "BTC/USDT"
        timeframe = "1h"
        start_date = "2021-06-01T00:00:00Z"
        end_date = "2021-06-02T00:00:00Z"

        df = data_manager.fetch_ohlcv(pair, timeframe, start_date, end_date)
        until_timestamp = pd.Timestamp(1622592000000, unit='ms')

        assert not df.empty
        assert df.index.max() <= until_timestamp

        expected_index = pd.to_datetime([1622505600000, 1622592000000], unit='ms')
        expected_index.name = 'timestamp'
        pd.testing.assert_index_equal(df.index, expected_index)

        assert df.iloc[0]["close"] == 34500
        assert df.iloc[1]["close"] == 35000

    @patch("core.services.data_manager.ccxt.binance")
    def test_fetch_ohlcv_chunked(self, mock_ccxt, config_manager):
        mock_exchange = mock_ccxt.return_value
        mock_exchange.fetch_ohlcv.side_effect = [
            [[1622505600000, 34000, 35000, 33000, 34500, 1000]],
            [[1622592000000, 34500, 35500, 34000, 35000, 1200]]
        ]
        mock_exchange.parse8601.side_effect = [
            1622505600000,  # start_date in milliseconds
            1622592000000   # end_date in milliseconds
        ]
        
        data_manager = DataManager(config_manager)
        data_manager._get_candle_limit = Mock(return_value=1)
        pair = "BTC/USDT"
        timeframe = "1h"
        start_date = "2021-06-01T00:00:00Z"
        end_date = "2021-06-02T00:00:00Z"
        df = data_manager.fetch_ohlcv(pair, timeframe, start_date, end_date)
    
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] == 2
        assert df.loc['2021-06-01'].close == 34500
        assert df.loc['2021-06-02'].close == 35000

    @patch("core.services.data_manager.ccxt.binance")
    def test_fetch_ohlcv_failure(self, mock_ccxt, config_manager):
        """Test failed fetch of OHLCV data raises DataFetchError."""
        mock_exchange = mock_ccxt.return_value
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")

        data_manager = DataManager(config_manager)
        pair = "BTC/USDT"
        timeframe = "1h"
        start_date = "2021-06-01T00:00:00Z"
        end_date = "2021-06-02T00:00:00Z"

        with pytest.raises(DataFetchError):
            data_manager.fetch_ohlcv(pair, timeframe, start_date, end_date)

    @patch("core.services.data_manager.time.sleep", return_value=None)
    @patch("core.services.data_manager.ccxt.binance")
    def test_fetch_with_retry(self, mock_ccxt, mock_sleep, config_manager):
        mock_exchange = mock_ccxt.return_value
        mock_exchange.fetch_ohlcv.side_effect = [Exception("API Error"), [[1622505600000, 34000, 35000, 33000, 34500, 1000]]]

        data_manager = DataManager(config_manager)
        pair = "BTC/USDT"
        timeframe = "1h"
        since = pd.Timestamp("2021-06-01T00:00:00Z").value // 10**6
        
        df = data_manager._fetch_ohlcv_once(pair, timeframe, since, since + 1000)
        
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] == 1
        mock_sleep.assert_called_once()