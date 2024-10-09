import argparse, logging, traceback
from core.services.exchange_service import ExchangeService
from strategies.grid_trading_strategy import GridTradingStrategy
from strategies.plotter import Plotter
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from core.order_handling.order_manager import OrderManager
from core.validation.transaction_validator import TransactionValidator
from core.order_handling.fee_calculator import FeeCalculator
from core.order_handling.balance_tracker import BalanceTracker
from core.order_handling.order_book import OrderBook
from core.grid_management.grid_manager import GridManager
from core.services.exceptions import UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError
from config.config_manager import ConfigManager
from config.config_validator import ConfigValidator
from config.exceptions import ConfigError
from utils.logging_config import setup_logging

class GridTradingBot:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config_manager = None
        self.data_manager = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        try:
            self.config_manager = self.initialize_config_manager()
            setup_logging(self.config_manager.get_logging_level(), self.config_manager.should_log_to_file(), self.config_manager.get_log_filename())
            self.logger.info("Starting Grid Trading Bot")
            
            self.order_book = OrderBook()
            self.data_manager = ExchangeService(self.config_manager)
            self.grid_manager = GridManager(self.config_manager)
            self.transaction_validator = TransactionValidator()
            self.fee_calculator = FeeCalculator(self.config_manager)
            self.balance_tracker = BalanceTracker(self.fee_calculator, self.config_manager.get_initial_balance(), 0)
            self.order_manager = OrderManager(self.config_manager, self.grid_manager, self.transaction_validator, self.balance_tracker, self.order_book)
            self.trading_performance_analyzer = TradingPerformanceAnalyzer(self.config_manager, self.order_book)
            self.plotter = Plotter(self.grid_manager, self.order_book)
            strategy = GridTradingStrategy(
                self.config_manager, 
                self.data_manager, 
                self.grid_manager, 
                self.order_manager, 
                self.balance_tracker, 
                self.trading_performance_analyzer, 
                self.plotter
            )
            strategy.initialize_strategy()
            strategy.simulate()
            strategy.plot_results()
            performance_summary = strategy.generate_performance_report()
        except ConfigError as e:
            self.handle_config_error(e)
        except (UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError) as e:
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
    parser = argparse.ArgumentParser(description="Spot Grid Trading Strategy.")
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file.')
    args = parser.parse_args()
    
    bot = GridTradingBot(args.config)
    bot.run()