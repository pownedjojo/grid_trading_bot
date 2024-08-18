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

    def get_exchange(self):
        return self.config.get('exchange', {})

    def get_pair(self):
        return self.config.get('pair', {})

    def get_timeframe(self):
        return self.config.get('timeframe', '1h')

    def get_period(self):
        return self.config.get('period', {})

    def get_initial_balance(self):
        return self.config.get('initial_balance', 10000)

    def get_grid_settings(self):
        return self.config.get('grid', {})

    def get_limits(self):
        return self.config.get('limits', {})

    def get_logging_level(self):
        log_level = self.config.get('logging', {}).get('log_level', 'INFO')
        return getattr(logging, log_level.upper(), logging.INFO)