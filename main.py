import argparse, logging, traceback
from data.data_manager import DataManager
from strategies.grid import GridTradingStrategy
from order_management.order_manager import OrderManager
from order_management.transaction_validator import TransactionValidator
from order_management.fee_calculator import FeeCalculator
from order_management.balance_tracker import BalanceTracker
from strategies.plotter import Plotter
from strategies.grid_manager import GridManager
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from config.logging_config import setup_logging
from config.config_manager import ConfigManager
from config.config_validator import ConfigValidator
from config.exceptions import ConfigError
from data.exceptions import UnsupportedExchangeError, DataFetchError

class GridTradingBot:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config_manager = None
        self.data_manager = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        try:
            self.config_manager = self.initialize_config_manager()
            setup_logging(self.config_manager.get_logging_level())
            self.logger.info("Starting Grid Trading Bot")

            self.data_manager = DataManager(self.config_manager)
            self.grid_manager = GridManager(self.config_manager)
            self.transaction_validator = TransactionValidator()
            self.fee_calculator = FeeCalculator(self.config_manager)
            self.balance_tracker = BalanceTracker(self.config_manager.get_initial_balance(), 0)
            self.order_manager = OrderManager(self.config_manager, self.grid_manager, self.transaction_validator, self.fee_calculator, self.balance_tracker)
            self.trading_performance_analyzer = TradingPerformanceAnalyzer(self.config_manager, self.order_manager)
            self.plotter = Plotter(self.config_manager, self.grid_manager, self.order_manager)
            strategy = GridTradingStrategy(
                self.config_manager, 
                self.data_manager, 
                self.grid_manager, 
                self.order_manager, 
                self.balance_tracker, 
                self.trading_performance_analyzer, 
                self.plotter
            )
            strategy.simulate()
            strategy.plot_results()
            performance_summary = strategy.generate_performance_report()
        except ConfigError as e:
            self.handle_config_error(e)
        except (UnsupportedExchangeError, DataFetchError) as e:
            self.handle_data_manager_error(e)
        except Exception as e:
            self.handle_general_error(e)

    def initialize_config_manager(self):
        try:
            return ConfigManager(self.config_path, ConfigValidator())
        except ConfigError as e:
            raise e

    def handle_config_error(self, exception):
        self.logger.error(f"Configuration error: {exception}")
        exit(1)
    
    def handle_data_manager_error(self, exception):
        self.logger.error(f"Data Manager error: {exception}")
        exit(1)

    def handle_general_error(self, exception):
        self.logger.error(f"An unexpected error occurred: {exception}")
        self.logger.error(traceback.format_exc())
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest Spot Grid Trading Strategy.")
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file.')
    args = parser.parse_args()
    
    bot = GridTradingBot(args.config)
    bot.run()