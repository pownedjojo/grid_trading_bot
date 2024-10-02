import logging
from .exceptions import ConfigValidationError

class ConfigValidator:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate(self, config):
        missing_fields = []
        invalid_fields = []
        missing_fields += self._validate_required_fields(config)
        invalid_fields += self._validate_exchange(config)
        missing_fields += self._validate_pair(config)
        invalid_fields += self._validate_timeframe(config)
        missing_fields += self._validate_period(config)
        grid_missing, grid_invalid = self._validate_grid_settings(config)
        missing_fields += grid_missing
        invalid_fields += grid_invalid
        invalid_fields += self._validate_limits(config)
        logging_missing, logging_invalid = self._validate_logging(config)
        missing_fields += logging_missing
        invalid_fields += logging_invalid

        if missing_fields or invalid_fields:
            raise ConfigValidationError(missing_fields=missing_fields, invalid_fields=invalid_fields)

    def _validate_required_fields(self, config):
        required_fields = ['exchange', 'pair', 'timeframe', 'period', 'initial_balance', 'grid', 'limits', 'logging']
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            self.logger.error(f"Missing required fields: {missing_fields}")
        return missing_fields

    def _validate_exchange(self, config):
        invalid_fields = []
        exchange = config.get('exchange', {})
        
        if not exchange.get('name'):
            self.logger.error("Exchange name is missing.")
            invalid_fields.append('exchange.name')
        
        trading_fee = exchange.get('trading_fee')
        if trading_fee is None or not isinstance(trading_fee, (float, int)) or trading_fee < 0:
            self.logger.error("Invalid or missing trading fee.")
            invalid_fields.append('exchange.trading_fee')

        return invalid_fields

    def _validate_pair(self, config):
        missing_fields = []
        pair = config.get('pair', {})

        if not pair.get('base_currency'):
            missing_fields.append('pair.base_currency')
        if not pair.get('quote_currency'):
            missing_fields.append('pair.quote_currency')

        if missing_fields:
            self.logger.error(f"Missing pair configuration fields: {missing_fields}")
        
        return missing_fields

    def _validate_timeframe(self, config):
        invalid_fields = []
        valid_timeframes = ['1m', '5m', '15m', '1h', '1d']
        timeframe = config.get('timeframe', None)
        
        if timeframe not in valid_timeframes:
            self.logger.error(f"Invalid timeframe: {timeframe}. Must be one of {valid_timeframes}.")
            invalid_fields.append('timeframe')

        return invalid_fields

    def _validate_period(self, config):
        missing_fields = []
        period = config.get('period', {})
        start_date = period.get('start_date')
        end_date = period.get('end_date')

        if not start_date:
            missing_fields.append('period.start_date')
        if not end_date:
            missing_fields.append('period.end_date')

        if missing_fields:
            self.logger.error(f"Missing period fields: {missing_fields}")
        
        return missing_fields

    def _validate_grid_settings(self, config):
        missing_fields = []
        invalid_fields = []
        grid = config.get('grid', {})

        if grid.get('num_grids') is None:
            missing_fields.append('grid.num_grids')
        if grid.get('top_range') is None:
            missing_fields.append('grid.top_range')
        if grid.get('bottom_range') is None:
            missing_fields.append('grid.bottom_range')

        if grid.get('spacing_type') not in ['arithmetic', 'geometric']:
            self.logger.error("Grid spacing_type must be either 'arithmetic' or 'geometric'.")
            invalid_fields.append('grid.spacing_type')

        return missing_fields, invalid_fields

    def _validate_limits(self, config):
        invalid_fields = []
        limits = config.get('limits', {})
        take_profit = limits.get('take_profit', {})
        stop_loss = limits.get('stop_loss', {})

        if not isinstance(take_profit.get('is_active'), bool):
            self.logger.error("Take profit is_active flag must be a boolean.")
            invalid_fields.append('limits.take_profit.is_active')

        if not isinstance(stop_loss.get('is_active'), bool):
            self.logger.error("Stop loss is_active flag must be a boolean.")
            invalid_fields.append('limits.stop_loss.is_active')

        return invalid_fields

    def _validate_logging(self, config):
        missing_fields = []
        invalid_fields = []
        logging_settings = config.get('logging', {})

        log_level = logging_settings.get('log_level')
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level is None:
            missing_fields.append('logging.log_level')
        elif log_level.upper() not in valid_log_levels:
            self.logger.error(f"Invalid log level: {log_level}. Must be one of {valid_log_levels}.")
            invalid_fields.append('logging.log_level')

        if missing_fields:
            self.logger.error(f"Missing logging fields: {missing_fields}")
        
        return missing_fields, invalid_fields