import logging
from typing import Optional, Tuple
import pandas as pd
import numpy as np
from .base import TradingStrategy
from config.trading_mode import TradingMode
from core.bot_management.event_bus import EventBus, Events
from config.config_manager import ConfigManager
from core.services.exchange_interface import ExchangeInterface
from core.grid_management.grid_manager import GridManager
from core.order_handling.order_manager import OrderManager
from core.order_handling.balance_tracker import BalanceTracker
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from strategies.plotter import Plotter

class GridTradingStrategy(TradingStrategy):
    TICKER_REFRESH_INTERVAL = 3  # in seconds

    def __init__(
        self,
        config_manager: ConfigManager,
        event_bus: EventBus,
        exchange_service: ExchangeInterface,
        grid_manager: GridManager,
        order_manager: OrderManager,
        balance_tracker: BalanceTracker,
        trading_performance_analyzer: TradingPerformanceAnalyzer,
        trading_mode: TradingMode,
        trading_pair: str,
        plotter: Optional[Plotter] = None
    ):
        super().__init__(config_manager, balance_tracker)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.event_bus = event_bus
        self.exchange_service = exchange_service
        self.grid_manager = grid_manager
        self.order_manager = order_manager
        self.trading_performance_analyzer = trading_performance_analyzer
        self.trading_mode = trading_mode
        self.trading_pair = trading_pair
        self.plotter = plotter
        self.data = self._initialize_data() if self.trading_mode == TradingMode.BACKTEST else None
        self._running = True
    
    def _initialize_data(self) -> Optional[pd.DataFrame]:
        try:
            timeframe, start_date, end_date = self._extract_config()
            return self.exchange_service.fetch_ohlcv(self.trading_pair, timeframe, start_date, end_date)
        except Exception as e:
            self.logger.error(f"Failed to initialize data for backtest trading mode: {e}")
            return None
    
    def _extract_config(self) -> Tuple[str, str, str]:
        timeframe = self.config_manager.get_timeframe()
        start_date = self.config_manager.get_start_date()
        end_date = self.config_manager.get_end_date()
        return timeframe, start_date, end_date

    def initialize_strategy(self):
        self.grid_manager.initialize_grids_and_levels()
    
    async def stop(self):
        self._running = False
        await self.exchange_service.close_connection()
        self.logger.info("Trading execution stopped.")

    async def restart(self):
        if not self._running:
            self.logger.info("Restarting trading session.")
            await self.run()

    async def run(self):
        self._running = True        
        trigger_price = self.grid_manager.get_trigger_price()

        if self.trading_mode == TradingMode.BACKTEST:
            await self._run_backtest(trigger_price)
            self.logger.info("Ending backtest simulation")
            self._running = False
        else:
            await self._run_live_or_paper_trading(trigger_price)
    
    async def _run_live_or_paper_trading(self, trigger_price: float):
        self.logger.info(f"Starting {'live' if self.trading_mode == TradingMode.LIVE else 'paper'} trading")
        last_price: Optional[float] = None
        grid_orders_initialized = False

        async def on_ticker_update(current_price):
            nonlocal last_price, grid_orders_initialized
            try:
                if not self._running:
                    self.logger.info("Trading stopped; halting price updates.")
                    return
                
                grid_orders_initialized = await self._initialize_grid_orders_once(
                    current_price, 
                    trigger_price, 
                    grid_orders_initialized, 
                    last_price
                )

                if not grid_orders_initialized:
                    last_price = current_price
                    return

                if await self._handle_take_profit_stop_loss(current_price):
                    return
                
                last_price = current_price

            except Exception as e:
                self.logger.error(f"Error during ticker update: {e}", exc_info=True)
        
        try:
            await self.exchange_service.listen_to_ticker_updates(
                self.trading_pair, 
                on_ticker_update, 
                self.TICKER_REFRESH_INTERVAL
            )
        
        except Exception as e:
            self.logger.error(f"Error in live/paper trading loop: {e}", exc_info=True)
        
        finally:
            self.logger.info("Exiting live/paper trading loop.")

    async def _run_backtest(self, trigger_price: float) -> None:
        if self.data is None:
            self.logger.error("No data available for backtesting.")
            return

        self.logger.info("Starting backtest simulation")
        self.data['account_value'] = np.nan
        self.close_prices = self.data['close'].values
        self.high_prices = self.data['high'].values
        self.low_prices = self.data['low'].values
        timestamps = self.data.index
        self.data.loc[timestamps[0], 'account_value'] = self.balance_tracker.get_total_balance_value(price=self.close_prices[0])
        grid_orders_initialized = False
        last_price = None

        for i, (current_price, high_price, low_price, timestamp) in enumerate(zip(self.close_prices, self.high_prices, self.low_prices, timestamps)):
            grid_orders_initialized = await self._initialize_grid_orders_once(
                current_price, 
                trigger_price,
                grid_orders_initialized,
                last_price
            )

            if not grid_orders_initialized:
                self.data.loc[timestamps[i], 'account_value'] = self.balance_tracker.get_total_balance_value(price=current_price)
                last_price = current_price
                continue

            await self.order_manager.simulate_order_fills(high_price, low_price, timestamp)

            if await self._handle_take_profit_stop_loss(current_price):
                break

            self.data.loc[timestamp, 'account_value'] = self.balance_tracker.get_total_balance_value(current_price)
            last_price = current_price
    
    async def _initialize_grid_orders_once(
        self, 
        current_price: float, 
        trigger_price: float, 
        grid_orders_initialized: bool,
        last_price: Optional[float] = None
    ) -> bool:
        if grid_orders_initialized:
            return True
        
        if last_price is None:
            self.logger.debug("No previous price recorded yet. Waiting for the next price update.")
            return False

        if last_price <= trigger_price <= current_price or last_price == trigger_price:
            self.logger.info(f"Current price {current_price} reached trigger price {trigger_price}. Will perform initial purhcase")
            await self.order_manager.perform_initial_purchase(current_price)
            self.logger.info(f"Initial purchase done, will initialize grid orders")
            await self.order_manager.initialize_grid_orders(current_price)
            return True

        self.logger.info(f"Current price {current_price} did not cross trigger price {trigger_price}. Last price: {last_price}.")
        return False

    def generate_performance_report(self) -> Tuple[dict, list]:
        if self.trading_mode == TradingMode.BACKTEST:
            final_price = self.close_prices[-1]
            return self.trading_performance_analyzer.generate_performance_summary(
                self.data, 
                self.balance_tracker.get_adjusted_fiat_balance(), 
                self.balance_tracker.get_adjusted_crypto_balance(), 
                final_price,
                self.balance_tracker.total_fees
            )
        else:
            self.logger.info("Performance report is not available for live/paper trading mode.")
            return {}, []

    def plot_results(self) -> None:
        if self.trading_mode == TradingMode.BACKTEST:
            self.plotter.plot_results(self.data)
        else:
            self.logger.info("Plotting is not available for live/paper trading mode.")
    
    async def _handle_take_profit_stop_loss(self, current_price: float) -> bool:
        if await self._check_take_profit_stop_loss(current_price):
            self.logger.info("Take-profit or stop-loss triggered, ending trading session.")
            await self.event_bus.publish(Events.STOP_BOT, "TP or SL hit.")
            return True
        return False

    async def _check_take_profit_stop_loss(
        self, 
        current_price: float
    ) -> bool:
        if self.balance_tracker.crypto_balance == 0:
            return False

        if self.config_manager.is_take_profit_enabled() and current_price >= self.config_manager.get_take_profit_threshold():
            await self.order_manager.execute_take_profit_or_stop_loss_order(current_price=current_price, take_profit_order=True)
            return True

        if self.config_manager.is_stop_loss_enabled() and current_price <= self.config_manager.get_stop_loss_threshold():
            await self.order_manager.execute_take_profit_or_stop_loss_order(current_price=current_price, stop_loss_order=True)
            return True

        return False
    
    def get_formatted_orders(self):
        return self.trading_performance_analyzer.get_formatted_orders()