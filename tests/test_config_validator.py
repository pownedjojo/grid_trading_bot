import pytest
from unittest.mock import Mock
from config.config_validator import ConfigValidator
from config.exceptions import ConfigValidationError

class TestConfigValidator:
    @pytest.fixture
    def config_validator(self):
        return ConfigValidator()

    def test_validate_valid_config(self, config_validator, valid_config):
        try:
            config_validator.validate(valid_config)
        except ConfigValidationError:
            pytest.fail("Valid configuration raised ConfigValidationError")

    def test_validate_missing_required_fields(self, config_validator):
        invalid_config = {
            'exchange': {}, 
            'pair': {}, 
            'trading_settings': {}, 
            'grid_strategy': {}, 
            'risk_management': {}, 
            'logging': {}
        }
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(invalid_config)
        
        missing_fields = excinfo.value.missing_fields
        invalid_fields = excinfo.value.invalid_fields

        assert 'pair.base_currency' in missing_fields
        assert 'pair.quote_currency' in missing_fields
        assert 'trading_settings.initial_balance' in missing_fields
        assert 'trading_settings.period.start_date' in missing_fields
        assert 'trading_settings.period.end_date' in missing_fields
        assert 'grid_strategy.num_grids' in missing_fields
        assert 'grid_strategy.range.top' in missing_fields
        assert 'grid_strategy.range.bottom' in missing_fields
        assert 'logging.log_level' in missing_fields

        assert 'exchange.name' in invalid_fields
        assert 'exchange.trading_fee' in invalid_fields
        assert 'trading_settings.timeframe' in invalid_fields

    def test_validate_invalid_exchange(self, config_validator, valid_config):
        valid_config['exchange'] = {'name': '', 'trading_fee': -0.01}  # Invalid exchange
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'exchange.name' in excinfo.value.invalid_fields
        assert 'exchange.trading_fee' in excinfo.value.invalid_fields

    def test_validate_invalid_timeframe(self, config_validator, valid_config):
        valid_config['trading_settings']['timeframe'] = '3h'  # Invalid timeframe
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'trading_settings.timeframe' in excinfo.value.invalid_fields

    def test_validate_missing_period_fields(self, config_validator, valid_config):
        valid_config['trading_settings']['period'] = {}  # Missing start and end date
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'trading_settings.period.start_date' in excinfo.value.missing_fields
        assert 'trading_settings.period.end_date' in excinfo.value.missing_fields

    def test_validate_invalid_grid_settings(self, config_validator, valid_config):
        # Test missing num_grids
        valid_config['grid_strategy']['num_grids'] = None
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'grid_strategy.num_grids' in excinfo.value.missing_fields

        # Test invalid top/bottom range (bottom should be less than top)
        valid_config['grid_strategy']['range'] = {'top': 2800, 'bottom': 2850}  # Invalid range
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'grid_strategy.range.top' in excinfo.value.invalid_fields
        assert 'grid_strategy.range.bottom' in excinfo.value.invalid_fields

        # Test invalid spacing type
        valid_config['grid_strategy']['spacing']['type'] = 'invalid_type'  # Invalid spacing type
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'grid_strategy.spacing.type' in excinfo.value.invalid_fields

        # Test missing percentage_spacing when spacing type is 'geometric'
        valid_config['grid_strategy']['spacing'] = {'type': 'geometric', 'percentage_spacing': None}
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'grid_strategy.spacing.percentage_spacing' in excinfo.value.missing_fields

        # Test invalid trade_percentage
        valid_config['grid_strategy']['trade_percentage'] = -0.5  # Invalid trade percentage
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'grid_strategy.trade_percentage' in excinfo.value.invalid_fields

    def test_validate_limits_invalid_type(self, config_validator, valid_config):
        valid_config['risk_management'] = {
            'take_profit': {'enabled': 'yes'},  # Invalid boolean
            'stop_loss': {'enabled': 1}  # Invalid boolean
        }
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'risk_management.take_profit.enabled' in excinfo.value.invalid_fields
        assert 'risk_management.stop_loss.enabled' in excinfo.value.invalid_fields

    def test_validate_logging_invalid_level(self, config_validator, valid_config):
        valid_config['logging'] = {
            'log_level': 'VERBOSE',  # Invalid log level
            'log_to_file': True,
            'log_file_path': 'logs/trading.log'
        }
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'logging.log_level' in excinfo.value.invalid_fields

    def test_validate_logging_missing_level(self, config_validator, valid_config):
        valid_config['logging'] = {
            'log_to_file': True,
            'log_file_path': 'logs/trading.log'  # Missing log_level
        }
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'logging.log_level' in excinfo.value.missing_fields