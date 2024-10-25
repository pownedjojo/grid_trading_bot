import argparse, logging, traceback, cProfile, pstats, io, os, json
from datetime import datetime, timedelta
import pandas as pd
from utils.arg_parser import parse_and_validate_console_args
from utils.performance_results_saver import save_or_append_performance_results
from concurrent.futures import ThreadPoolExecutor
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
    def __init__(self, config_path, save_performance_results_path=None, no_plot=False):
        self.config_path = config_path
        self.save_performance_results_path = save_performance_results_path
        self.no_plot = no_plot
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        try:
            self.config_manager = self._initialize_config_manager()
            setup_logging(self.config_manager.get_logging_level(), self.config_manager.should_log_to_file(), self.config_manager.get_log_filename())
            self.logger.info("Starting Grid Trading Bot")
            
            self.order_book = OrderBook()
            self.exchange_service = ExchangeService(self.config_manager)
            self.grid_manager = GridManager(self.config_manager)
            self.transaction_validator = TransactionValidator()
            self.fee_calculator = FeeCalculator(self.config_manager)
            self.balance_tracker = BalanceTracker(self.fee_calculator, self.config_manager.get_initial_balance(), 0)
            self.order_manager = OrderManager(self.config_manager, self.grid_manager, self.transaction_validator, self.balance_tracker, self.order_book)
            self.trading_performance_analyzer = TradingPerformanceAnalyzer(self.config_manager, self.order_book)
            self.plotter = Plotter(self.grid_manager, self.order_book)
            strategy = GridTradingStrategy(
                self.config_manager, 
                self.exchange_service, 
                self.grid_manager, 
                self.order_manager, 
                self.balance_tracker, 
                self.trading_performance_analyzer, 
                self.plotter
            )
            strategy.initialize_strategy()
            strategy.simulate()

            if not self.no_plot:
                strategy.plot_results()

            performance_summary, formatted_orders = strategy.generate_performance_report()    
            return {"config": self.config_path, "performance_summary": performance_summary, "orders": formatted_orders}
        except ConfigError as e:
            self._handle_config_error(e)
        except (UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError) as e:
            self._handle_exchange_service_error(e)
        except Exception as e:
            self._handle_general_error(e)

    def _initialize_config_manager(self):
        try:
            return ConfigManager(self.config_path, ConfigValidator())
        except ConfigError as e:
            raise e

    def _handle_config_error(self, exception):
        self.logger.error(f"Configuration error: {exception}")
        exit(1)
    
    def _handle_exchange_service_error(self, exception):
        self.logger.error(f"Exchange Service error: {exception}")
        exit(1)

    def _handle_general_error(self, exception):
        self.logger.error(f"An unexpected error occurred: {exception}")
        self.logger.error(traceback.format_exc())
        exit(1)

def run_bot_with_config(config_path, profile=False, save_performance_results_path=None, no_plot=False):
    bot = GridTradingBot(config_path, save_performance_results_path, no_plot)

    if profile:
        cProfile.runctx("bot.run()", globals(), locals(), "profile_results.prof")
        return None
    else:
        return bot.run()

if __name__ == "__main__":
    args = parse_and_validate_console_args()
    
    with ThreadPoolExecutor() as executor:
        futures = []
        for config_path in args.config:
            futures.append(executor.submit(run_bot_with_config, config_path, args.profile, args.save_performance_results, args.no_plot))
        
        for future in futures:
            result = future.result()
            if result and args.save_performance_results:
                save_or_append_performance_results(result, args.save_performance_results)