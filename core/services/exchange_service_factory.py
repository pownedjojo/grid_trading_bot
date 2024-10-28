from .backtest_exchange_service import BacktestExchangeService
from .live_exchange_service import LiveExchangeService
from config.trading_modes import TradingMode

class ExchangeServiceFactory:
    @staticmethod
    def create_exchange_service(config_manager, trading_mode: TradingMode):
        if trading_mode == TradingMode.BACKTEST:
            return BacktestExchangeService(config_manager)
        elif trading_mode == TradingMode.PAPER_TRADING:
            return LiveExchangeService(config_manager, paper=True)
        elif trading_mode == TradingMode.LIVE:
            return LiveExchangeService(config_manager, paper=False)
        else:
            raise ValueError(f"Unsupported trading mode: {trading_mode}")