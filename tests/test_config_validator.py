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
        invalid_config = {'exchange': {}, 'pair': {}, 'timeframe': None}
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(invalid_config)
        
        missing_fields = excinfo.value.missing_fields
        invalid_fields = excinfo.value.invalid_fields

        # Check for specific missing fields
        assert 'period' in missing_fields
        assert 'initial_balance' in missing_fields
        assert 'grid' in missing_fields
        assert 'limits' in missing_fields
        assert 'logging' in missing_fields
        assert 'pair.base_currency' in missing_fields
        assert 'pair.quote_currency' in missing_fields

        # Check for specific invalid fields
        assert 'exchange.name' in invalid_fields
        assert 'exchange.trading_fee' in invalid_fields
        assert 'timeframe' in invalid_fields

    def test_validate_invalid_exchange(self, config_validator, valid_config):
        valid_config['exchange'] = {'name': '', 'trading_fee': -0.01}  # Invalid exchange
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'exchange.name' in excinfo.value.invalid_fields
        assert 'exchange.trading_fee' in excinfo.value.invalid_fields

    def test_validate_invalid_timeframe(self, config_validator, valid_config):
        valid_config['timeframe'] = '2h'  # Invalid timeframe
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'timeframe' in excinfo.value.invalid_fields

    def test_validate_missing_period_fields(self, config_validator, valid_config):
        valid_config['period'] = {}  # Missing start and end date
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'period.start_date' in excinfo.value.missing_fields
        assert 'period.end_date' in excinfo.value.missing_fields

    def test_validate_invalid_grid_settings(self, config_validator, valid_config):
        valid_config['grid'] = {'spacing_type': 'invalid'}  # Missing grid settings
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'grid.num_grids' in excinfo.value.missing_fields
        assert 'grid.spacing_type' in excinfo.value.invalid_fields

    def test_validate_limits_invalid_type(self, config_validator, valid_config):
        valid_config['limits'] = {'take_profit': {'is_active': 'yes'}, 'stop_loss': {'is_active': 1}}
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'limits.take_profit.is_active' in excinfo.value.invalid_fields
        assert 'limits.stop_loss.is_active' in excinfo.value.invalid_fields

    def test_validate_logging_invalid_level(self, config_validator, valid_config):
        valid_config['logging'] = {'log_level': 'VERBOSE'}
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'logging.log_level' in excinfo.value.invalid_fields

    def test_validate_logging_missing_level(self, config_validator, valid_config):
        valid_config['logging'] = {}  # Missing log_level
        with pytest.raises(ConfigValidationError) as excinfo:
            config_validator.validate(valid_config)
        assert 'logging.log_level' in excinfo.value.missing_fields