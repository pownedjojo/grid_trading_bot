import argparse, logging
from data.exchanges import load_data
from strategies.grid import GridTradingStrategy
from config.logging_config import setup_logging
from config.config_manager import ConfigManager
from config.exceptions import ConfigFileNotFoundError, ConfigParseError, ConfigValidationError

class GridTradingBot:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config_manager = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        try:
            self.config_manager = self.initialize_config_manager()
            setup_logging(self.config_manager.get_logging_level())
            
            self.logger.info("Starting Grid Trading Bot")
            
            exchange, pair, timeframe, start_date, end_date = self.extract_config()
            data = self.load_and_log_data(exchange, pair, timeframe, start_date, end_date)
            
            strategy = GridTradingStrategy(self.config_manager)
            strategy.data = data
            strategy.simulate()
            strategy.plot_results()
            performance_summary = strategy.calculate_performance_metrics()

        except (ConfigFileNotFoundError, ConfigParseError, ConfigValidationError) as e:
            self.handle_config_error(e)
        except Exception as e:
            # TODO: Handle OrderExecutionError, DataFetching error, etc..
            self.handle_general_error(e)

    def initialize_config_manager(self):
        try:
            return ConfigManager(self.config_path)
        except (ConfigFileNotFoundError, ConfigParseError, ConfigValidationError) as e:
            raise e

    def extract_config(self):
        exchange = self.config_manager.get_exchange()['name']
        pair_config = self.config_manager.get_pair()
        pair = f"{pair_config['base_currency']}/{pair_config['quote_currency']}"
        timeframe = self.config_manager.get_timeframe()
        period = self.config_manager.get_period()
        start_date = period['start_date']
        end_date = period['end_date']
        return exchange, pair, timeframe, start_date, end_date

    def load_and_log_data(self, exchange, pair, timeframe, start_date, end_date):
        self.logger.info(f"Loading data from {exchange} for {pair} from {start_date} to {end_date}")
        return load_data(exchange, pair, timeframe, start_date, end_date)

    def handle_config_error(self, exception):
        self.logger.error(f"Configuration error: {exception}")
        exit(1)

    def handle_general_error(self, exception):
        self.logger.error(f"An unexpected error occurred: {exception}")
        exit(1)

def setup_logging(log_level):
    logging.basicConfig(level=log_level)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest Spot Grid Trading Strategy.")
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file.')
    args = parser.parse_args()
    
    bot = GridTradingBot(args.config)
    bot.run()