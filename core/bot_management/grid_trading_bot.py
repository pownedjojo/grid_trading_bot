import logging, traceback
from typing import Optional, Dict, Any
from core.services.exchange_service_factory import ExchangeServiceFactory
from strategies.grid_trading_strategy import GridTradingStrategy
from strategies.plotter import Plotter
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from core.order_handling.order_manager import OrderManager
from core.validation.transaction_validator import TransactionValidator
from core.order_handling.order_status_tracker import OrderStatusTracker
from core.bot_management.event_bus import EventBus, Events
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
        event_bus: EventBus,
        save_performance_results_path: Optional[str] = None, 
        no_plot: bool = False
    ):
        try:
            self.config_path = config_path
            self.config_manager = config_manager
            self.notification_handler = notification_handler
            self.event_bus = event_bus
            self.event_bus.subscribe(Events.STOP_BOT, self._handle_stop_bot_event)
            self.event_bus.subscribe(Events.START_BOT, self._handle_start_bot_event)
            self.save_performance_results_path = save_performance_results_path
            self.no_plot = no_plot
            self.logger = logging.getLogger(self.__class__.__name__)
            self.trading_mode = self.config_manager.get_trading_mode()
            self.logger.info(f"Starting Grid Trading Bot in {self.trading_mode.value} mode")
            self.is_running = False

            self.exchange_service = ExchangeServiceFactory.create_exchange_service(self.config_manager, self.trading_mode)
            order_execution_strategy = OrderExecutionStrategyFactory.create(self.config_manager, self.exchange_service)
            grid_manager = GridManager(self.config_manager)
            transaction_validator = TransactionValidator()
            fee_calculator = FeeCalculator(self.config_manager)
            self.balance_tracker = BalanceTracker(self.event_bus, fee_calculator, self.config_manager.get_initial_balance(), 0)
            order_book = OrderBook()

            self.order_status_tracker = OrderStatusTracker(
                order_book=order_book,
                order_execution_strategy=order_execution_strategy,
                event_bus=self.event_bus,
                polling_interval=5.0,
            )

            order_manager = OrderManager(
                self.config_manager,
                grid_manager,
                transaction_validator,
                self.balance_tracker,
                order_book,
                self.event_bus,
                order_execution_strategy,
                self.notification_handler
            )
            
            trading_performance_analyzer = TradingPerformanceAnalyzer(self.config_manager, order_book)
            plotter = Plotter(grid_manager, order_book) if self.trading_mode == TradingMode.BACKTEST else None
            self.strategy = GridTradingStrategy(
                self.config_manager,
                self.event_bus,
                self.exchange_service,
                grid_manager,
                order_manager,
                self.balance_tracker,
                trading_performance_analyzer,
                plotter
            )

        except (UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError) as e:
            self.logger.error(f"{type(e).__name__}: {e}")
            exit(1)            
        except Exception as e:
            self.logger.error("An unexpected error occurred.")
            self.logger.error(traceback.format_exc())
            exit(1)

    async def run(self) -> Optional[Dict[str, Any]]:
        try:
            self.is_running = True

            self.order_status_tracker.start_tracking()
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
        
        finally:
            self.is_running = False

    async def _handle_stop_bot_event(self, reason: str) -> None:
        if not self.is_running:
            self.logger.warning(f"Stop event received but bot is already stopped: {reason}")
            return

        self.logger.info(f"Handling STOP_BOT event: {reason}")
        await self._stop()

    async def _handle_start_bot_event(self, reason: str) -> None:
        if self.is_running:
            self.logger.warning(f"Start event received but bot is already running: {reason}")
            return

        self.logger.info(f"Handling START_BOT event: {reason}")
        await self.restart()
    
    async def _stop(self) -> None:
        if not self.is_running:
            self.logger.info("Bot is not running. Nothing to stop.")
            return

        self.logger.info("Stopping Grid Trading Bot...")

        try:
            self.order_status_tracker.stop_tracking()
            await self.strategy.stop()
            self.is_running = False

        except Exception as e:
            self.logger.error(f"Error while stopping components: {e}", exc_info=True)

        self.event_bus.publish_sync(Events.STOP_BOT, "Bot stopped")
        self.logger.info("Grid Trading Bot has been stopped.")
    
    async def restart(self) -> None:
        if self.is_running:
            self.logger.info("Bot is already running. Restarting...")
            await self._stop()

        self.logger.info("Restarting Grid Trading Bot...")
        self.is_running = True

        try:
            self.order_status_tracker.start_tracking()
            await self.strategy.restart()

        except Exception as e:
            self.logger.error(f"Error while restarting components: {e}", exc_info=True)

        self.logger.info("Grid Trading Bot has been restarted.")

    def _generate_and_log_performance(self) -> Optional[Dict[str, Any]]:
        performance_summary, formatted_orders = self.strategy.generate_performance_report()
        return {
            "config": self.config_path,
            "performance_summary": performance_summary,
            "orders": formatted_orders
        }
    
    async def get_bot_health_status(self) -> dict:
        health_status = {
            "strategy": await self._check_strategy_health(),
            "exchange_status": await self._get_exchange_status()
        }

        health_status["overall"] = all(health_status.values())
        return health_status
    
    async def _check_strategy_health(self) -> bool:
        if not self.is_running:
            self.logger.warning("Bot has stopped unexpectedly.")
            return False
        return True

    async def _get_exchange_status(self) -> str:
        exchange_status = await self.exchange_service.get_exchange_status()
        return exchange_status.get("status", "unknown")
    
    async def get_balance(self) -> Dict[str, float]:
        return {
            "fiat": self.balance_tracker.balance,
            "crypto": self.balance_tracker.crypto_balance,
        }