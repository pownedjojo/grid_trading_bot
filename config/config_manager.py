import json, os, logging
from .exceptions import ConfigFileNotFoundError, ConfigValidationError, ConfigParseError

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.logger.error(f"Config file {self.config_file} does not exist.")
            raise ConfigFileNotFoundError(self.config_file)
        
        with open(self.config_file, 'r') as file:
            try:
                self.config = json.load(file)
                self.validate_config()
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse config file {self.config_file}: {e}")
                raise ConfigParseError(self.config_file, e)

    def validate_config(self):
        required_fields = ['exchange', 'pair', 'timeframe', 'period', 'initial_balance', 'grid', 'limits', 'logging']
        missing_fields = [field for field in required_fields if field not in self.config]
        if missing_fields:
            self.logger.error(f"Missing required config fields: {missing_fields}")
            raise ConfigValidationError(missing_fields)
        
        self.logger.info("Configuration validation passed.")

    def get(self, key, default=None):
        return self.config.get(key, default)

    # --- General Accessor Methods ---
    def get_exchange(self):
        return self.config.get('exchange', {})
    
    def get_exchange_name(self):
        exchange = self.get_exchange()
        return exchange.get('name', None)

    def get_trading_fee(self):
        exchange = self.get_exchange()
        return exchange.get('trading_fee', 0)

    def get_pair(self):
        return self.config.get('pair', {})
    
    def get_base_currency(self):
        pair = self.get_pair()
        return pair.get('base_currency', None)

    def get_quote_currency(self):
        pair = self.get_pair()
        return pair.get('quote_currency', None)

    def get_timeframe(self):
        return self.config.get('timeframe', '1h')

    def get_period(self):
        return self.config.get('period', {})
    
    def get_start_date(self):
        period = self.get_period()
        return period.get('start_date', None)

    def get_end_date(self):
        period = self.get_period()
        return period.get('end_date', None)

    def get_initial_balance(self):
        return self.config.get('initial_balance', 10000)

    def get_logging_level(self):
        log_level = self.config.get('logging', {}).get('log_level', 'INFO')
        return getattr(logging, log_level.upper(), logging.INFO)

    # --- Grid Accessor Methods ---
    def get_grid_settings(self):
        return self.config.get('grid', {})

    def get_num_grids(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('num_grids', None)

    def get_top_range(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('top_range', None)

    def get_bottom_range(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('bottom_range', None)

    def get_spacing_type(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('spacing_type', None)

    def get_grid_spacing(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('grid_spacing', None)

    def get_percentage_spacing(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('percentage_spacing', None)

    # --- Limits (Take Profit / Stop Loss) Accessor Methods ---
    def get_limits(self):
        return self.config.get('limits', {})

    def get_take_profit(self):
        limits = self.get_limits()
        return limits.get('take_profit', {})

    def is_take_profit_active(self):
        take_profit = self.get_take_profit()
        return take_profit.get('is_active', False)

    def get_take_profit_threshold(self):
        take_profit = self.get_take_profit()
        return take_profit.get('threshold', None)

    def get_stop_loss(self):
        limits = self.get_limits()
        return limits.get('stop_loss', {})

    def is_stop_loss_active(self):
        stop_loss = self.get_stop_loss()
        return stop_loss.get('is_active', False)

    def get_stop_loss_threshold(self):
        stop_loss = self.get_stop_loss()
        return stop_loss.get('threshold', None)