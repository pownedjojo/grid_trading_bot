import json, os, logging
from .exceptions import ConfigFileNotFoundError, ConfigParseError

class ConfigManager:
    def __init__(self, config_file, config_validator):
        self.config_file = config_file
        self.config_validator = config_validator
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
                self.config_validator.validate(self.config)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse config file {self.config_file}: {e}")
                raise ConfigParseError(self.config_file, e)

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
    
    def get_trading_settings(self):
        return self.config.get('trading_settings', {})

    def get_timeframe(self):
        trading_settings = self.get_trading_settings()
        return trading_settings.get('timeframe', '1h')

    def get_period(self):
        trading_settings = self.get_trading_settings()
        return trading_settings.get('period', {})
    
    def get_start_date(self):
        period = self.get_period()
        return period.get('start_date', None)

    def get_end_date(self):
        period = self.get_period()
        return period.get('end_date', None)

    def get_initial_balance(self):
        trading_settings = self.get_trading_settings()
        return trading_settings.get('initial_balance', 10000)

    def get_logging_level(self):
        log_level = self.config.get('logging', {}).get('log_level', 'INFO')
        return getattr(logging, log_level.upper(), logging.INFO)

    # --- Grid Accessor Methods ---
    def get_grid_settings(self):
        return self.config.get('grid_strategy', {})

    def get_num_grids(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('num_grids', None)
    
    def get_grid_range(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('range', {})

    def get_top_range(self):
        grid_range = self.get_grid_range()
        return grid_range.get('top', None)

    def get_bottom_range(self):
        grid_range = self.get_grid_range()
        return grid_range.get('bottom', None)
    
    def get_grid_spacing(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('spacing', {})

    def get_spacing_type(self):
        grid_spacing = self.get_grid_spacing()
        return grid_spacing.get('type', None)

    def get_percentage_spacing(self):
        grid_spacing = self.get_grid_spacing()
        return grid_spacing.get('percentage_spacing', None)
    
    def get_fixed_spacing(self):
        grid_spacing = self.get_grid_spacing()
        return grid_spacing.get('fixed_spacing', None)
    
    def get_trade_percentage(self):
        grid_settings = self.get_grid_settings()
        return grid_settings.get('trade_percentage', None)

    # --- Risk management (Take Profit / Stop Loss) Accessor Methods ---
    def get_risk_management(self):
        return self.config.get('risk_management', {})

    def get_take_profit(self):
        risk_management = self.get_risk_management()
        return risk_management.get('take_profit', {})

    def is_take_profit_enabled(self):
        take_profit = self.get_take_profit()
        return take_profit.get('enabled', False)

    def get_take_profit_threshold(self):
        take_profit = self.get_take_profit()
        return take_profit.get('threshold', None)

    def get_stop_loss(self):
        risk_management = self.get_risk_management()
        return risk_management.get('stop_loss', {})

    def is_stop_loss_enabled(self):
        stop_loss = self.get_stop_loss()
        return stop_loss.get('enabled', False)

    def get_stop_loss_threshold(self):
        stop_loss = self.get_stop_loss()
        return stop_loss.get('threshold', None)
    
    # --- Logging Accessor Methods ---
    def get_logging(self):
        return self.config.get('logging', {})
    
    def get_logging_level(self):
        logging = self.get_logging()
        return logging.get('log_level', {})
    
    def should_log_to_file(self):
        logging = self.get_logging()
        return logging.get('log_to_file', False)

    def get_log_filename(self):
        logging = self.get_logging()
        return logging.get('log_filename', 'grid_trading_bot.log')