import logging, traceback, cProfile, asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
from utils.arg_parser import parse_and_validate_console_args
from utils.performance_results_saver import save_or_append_performance_results
from core.bot_controller.bot_controller import BotController
from core.services.exchange_service_factory import ExchangeServiceFactory
from strategies.grid_trading_strategy import GridTradingStrategy
from strategies.plotter import Plotter
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from core.order_handling.order_manager import OrderManager
from core.validation.transaction_validator import TransactionValidator
from core.order_handling.fee_calculator import FeeCalculator
from core.order_handling.balance_tracker import BalanceTracker
from core.order_handling.order_book import OrderBook
from core.grid_management.grid_manager import GridManager
from core.order_handling.execution_strategy.order_execution_strategy_factory import OrderExecutionStrategyFactory
from core.services.exceptions import UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError
from config.config_manager import ConfigManager
from config.config_validator import ConfigValidator
from config.exceptions import ConfigError
from config.trading_mode import TradingMode
from utils.logging_config import setup_logging

class GridTradingBot:
    def __init__(self, config_path: str, save_performance_results_path: Optional[str] = None, no_plot: bool = False):
        try:
            self.config_path = config_path
            self.save_performance_results_path = save_performance_results_path
            self.no_plot = no_plot
            self.logger = logging.getLogger(self.__class__.__name__)
            self.config_manager = self._initialize_config_manager()
            setup_logging(
                self.config_manager.get_logging_level(),
                self.config_manager.should_log_to_file(),
                self.config_manager.get_log_filename()
            )
            self.trading_mode = self.config_manager.get_trading_mode()
            self.logger.info(f"Starting Grid Trading Bot in {self.trading_mode.value} mode")

            self.exchange_service = ExchangeServiceFactory.create_exchange_service(self.config_manager, self.trading_mode)
            self.order_execution_strategy = OrderExecutionStrategyFactory.create(self.config_manager, self.exchange_service)
            self.grid_manager = GridManager(self.config_manager)
            self.transaction_validator = TransactionValidator()
            self.fee_calculator = FeeCalculator(self.config_manager)
            self.balance_tracker = BalanceTracker(self.fee_calculator, self.config_manager.get_initial_balance(), 0)
            self.order_book = OrderBook()
            self.order_manager = OrderManager(
                self.config_manager,
                self.grid_manager,
                self.transaction_validator,
                self.balance_tracker,
                self.order_book,
                self.order_execution_strategy
            )
            self.trading_performance_analyzer = TradingPerformanceAnalyzer(self.config_manager, self.order_book)
            self.plotter = Plotter(self.grid_manager, self.order_book) if self.trading_mode == TradingMode.BACKTEST else None
            self.strategy = GridTradingStrategy(
                self.config_manager,
                self.exchange_service,
                self.grid_manager,
                self.order_manager,
                self.balance_tracker,
                self.trading_performance_analyzer,
                self.plotter
            )

        except (ConfigError, UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError) as e:
            self._log_and_exit(e)
        except Exception as e:
            self.logger.error("An unexpected error occurred.")
            self.logger.error(traceback.format_exc())
            exit(1)

    async def run(self) -> Optional[Dict[str, Any]]:
        try:
            self.strategy.initialize_strategy()
            await self.strategy.run()

            if self.trading_mode == TradingMode.BACKTEST and not self.no_plot:
                self.strategy.plot_results()

            return self._generate_and_log_performance()

        except (ConfigError, UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError) as e:
            self._log_and_exit(e)

        except Exception as e:
            self.logger.error("An unexpected error occurred.")
            self.logger.error(traceback.format_exc())
            exit(1)

    def _initialize_config_manager(self) -> ConfigManager:
        try:
            return ConfigManager(self.config_path, ConfigValidator())
        except ConfigError as e:
            raise e

    def _generate_and_log_performance(self) -> Optional[Dict[str, Any]]:
        performance_summary, formatted_orders = self.strategy.generate_performance_report()
        
        if self.trading_mode == TradingMode.LIVE:
            self.logger.info("Live trading session completed. Performance data available.")
        elif self.trading_mode == TradingMode.PAPER_TRADING:
            self.logger.info("Paper trading session completed. Review the performance summary.")
        elif self.trading_mode == TradingMode.BACKTEST:
            return {
                "config": self.config_path,
                "performance_summary": performance_summary,
                "orders": formatted_orders
            }
        return None

    def _log_and_exit(self, exception: Exception) -> None:
        self.logger.error(f"{type(exception).__name__}: {exception}")
        exit(1)

async def run_bot_with_config(
    config_path: str,
    profile: bool = False, 
    save_performance_results_path: Optional[str] = None, 
    no_plot: bool = False
) -> Optional[Dict[str, Any]]:
    bot = GridTradingBot(config_path, save_performance_results_path, no_plot)
    bot_controller = BotController(bot.strategy, bot.balance_tracker, bot.trading_performance_analyzer)

    if profile:
        cProfile.runctx("asyncio.run(bot.run())", globals(), locals(), "profile_results.prof")
        return None
    else:
        if bot.trading_mode in {TradingMode.LIVE, TradingMode.PAPER_TRADING}:
            bot_controller = BotController(bot.strategy, bot.balance_tracker, bot.order_book)
            await asyncio.gather(bot.run(), bot_controller.command_listener())
        else:
            await bot.run()

if __name__ == "__main__":
    args = parse_and_validate_console_args()
    
    async def main():
        tasks = [
            run_bot_with_config(config_path, args.profile, args.save_performance_results, args.no_plot)
            for config_path in args.config
        ]
        
        results = await asyncio.gather(*tasks)
        if args.save_performance_results:
            for result in results:
                save_or_append_performance_results(result, args.save_performance_results)

    asyncio.run(main())