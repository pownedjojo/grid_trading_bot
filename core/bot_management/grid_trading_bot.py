import logging, traceback, os
from typing import Optional, Dict, Any
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
from config.trading_mode import TradingMode
from .notification.notification_handler import NotificationHandler

class GridTradingBot:
    def __init__(
        self, 
        config_path: str, 
        config_manager: ConfigManager,
        notification_handler: NotificationHandler,
        save_performance_results_path: Optional[str] = None, 
        no_plot: bool = False
    ):
        try:
            self.config_path = config_path
            self.config_manager = config_manager
            self.notification_handler = notification_handler
            self.save_performance_results_path = save_performance_results_path
            self.no_plot = no_plot
            self.logger = logging.getLogger(self.__class__.__name__)
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
                self.order_execution_strategy,
                self.notification_handler
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

        except (UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError) as e:
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

            if self.trading_mode == TradingMode.BACKTEST:
                return self._generate_and_log_performance()

        except Exception as e:
            self.logger.error(f"An unexpected error occurred {e}")
            self.logger.error(traceback.format_exc())
            exit(1)

    def _generate_and_log_performance(self) -> Optional[Dict[str, Any]]:
        performance_summary, formatted_orders = self.strategy.generate_performance_report()
        return {
            "config": self.config_path,
            "performance_summary": performance_summary,
            "orders": formatted_orders
        }

    def _log_and_exit(self, exception: Exception) -> None:
        self.logger.error(f"{type(exception).__name__}: {exception}")
        exit(1)
    
    async def is_healthy(self) -> dict:
        health_status = {
            "strategy": await self._check_strategy_health(),
            "exchange_status": await self._get_exchange_status()
        }

        health_status["overall"] = all(health_status.values())
        return health_status
    
    async def _check_strategy_health(self) -> bool:
        if not self.strategy._running:
            self.logger.warning("Strategy has stopped unexpectedly.")
            return False
        return True

    async def _get_exchange_status(self) -> str:
        exchange_status = await self.exchange_service.get_exchange_status()
        return exchange_status.get("status", "unknown")