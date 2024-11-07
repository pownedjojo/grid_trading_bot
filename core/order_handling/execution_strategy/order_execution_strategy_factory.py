from config.trading_mode import TradingMode
from config.config_manager import ConfigManager
from .live_order_execution_strategy import LiveOrderExecutionStrategy
from .backtest_order_execution_strategy import BacktestOrderExecutionStrategy
from .order_execution_strategy import OrderExecutionStrategy
from core.services.exchange_interface import ExchangeInterface

class OrderExecutionStrategyFactory:
    @staticmethod
    def create(
        config_manager: ConfigManager, 
        exchange_service: ExchangeInterface
    ) -> OrderExecutionStrategy:
        trading_mode = config_manager.get_trading_mode()

        if trading_mode == TradingMode.LIVE or trading_mode == TradingMode.PAPER_TRADING:
            return LiveOrderExecutionStrategy(exchange_service=exchange_service)
        elif trading_mode == TradingMode.BACKTEST:
            return BacktestOrderExecutionStrategy()
        else:
            raise ValueError(f"Unknown trading mode: {trading_mode}")