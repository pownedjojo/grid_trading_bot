from unittest.mock import patch, mock_open, Mock
import pytest
import json
from config.config_manager import ConfigManager
from config.exceptions import ConfigFileNotFoundError, ConfigParseError

class TestConfigManager:
    @pytest.fixture
    def mock_validator(self):
        return Mock()

    @pytest.fixture
    def config_manager(self, mock_validator, valid_config):
        # Mocking both open and os.path.exists to simulate a valid config file
        mocked_open = mock_open(read_data=json.dumps(valid_config))
        with patch("builtins.open", mocked_open), patch("os.path.exists", return_value=True):
            return ConfigManager("config.json", mock_validator)

    def test_load_config_valid(self, config_manager, valid_config, mock_validator):
        mock_validator.validate.assert_called_once_with(valid_config)
        assert config_manager.config == valid_config

    def test_load_config_file_not_found(self, mock_validator):
        with patch("os.path.exists", return_value=False):
            with pytest.raises(ConfigFileNotFoundError):
                ConfigManager("config.json", mock_validator)

    def test_load_config_json_decode_error(self, mock_validator):
        invalid_json = '{"invalid_json": '  # Malformed JSON
        mocked_open = mock_open(read_data=invalid_json)
        with patch("builtins.open", mocked_open), patch("os.path.exists", return_value=True):
            with pytest.raises(ConfigParseError):
                ConfigManager("config.json", mock_validator)

    def test_get_exchange_name(self, config_manager):
        assert config_manager.get_exchange_name() == "binance"

    def test_get_trading_fee(self, config_manager):
        assert config_manager.get_trading_fee() == 0.001

    def test_get_base_currency(self, config_manager):
        assert config_manager.get_base_currency() == "ETH"

    def test_get_quote_currency(self, config_manager):
        assert config_manager.get_quote_currency() == "USDT"

    def test_get_initial_balance(self, config_manager):
        assert config_manager.get_initial_balance() == 10000