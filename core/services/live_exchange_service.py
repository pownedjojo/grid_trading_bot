import ccxt, logging, time, asyncio, os
from typing import Dict, Union, Callable
from config.config_manager import ConfigManager
from utils.constants import CANDLE_LIMITS, TIMEFRAME_MAPPINGS
from .exchange_interface import ExchangeInterface
from .exceptions import UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError, MissingEnvironmentVariableError

class LiveExchangeService(ExchangeInterface):
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.exchange_name = self.config_manager.get_exchange_name()
        self.trading_mode = self.config_manager.get_trading_mode()
        self.exchange = self._initialize_exchange()
        self.api_key = self._get_env_variable("EXCHANGE_API_KEY")
        self.secret_key = self._get_env_variable("EXCHANGE_SECRET_KEY")
        self.connection_active = False
    
    def _get_env_variable(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise MissingEnvironmentVariableError(f"Missing required environment variable: {key}")
        return value

    def _initialize_exchange(self):
        try:
            exchange = getattr(ccxt, self.exchange_name)({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True
            })

            if self.trading_mode == TradingMode.PAPER_TRADING:
                self._enable_sandbox_mode(exchange)
            return exchange
        except AttributeError:
            raise UnsupportedExchangeError(f"The exchange '{self.exchange_name}' is not supported.")

    def _enable_sandbox_mode(self, exchange):
        if self.exchange_name == 'binance':
            exchange.set_sandbox_mode(True)
        elif self.exchange_name == 'kraken':
            exchange.urls['api'] = 'https://api.sandbox.kraken.com'
        else:
            self.logger.warning(f"No sandbox mode available for {self.exchange_name}. Running in live mode.")
    
    async def _subscribe_to_price_updates(self, pair: str, on_price_update: Callable[[float, float], None]):
        self.connection_active = True
        while self.connection_active:
            try:
                self.logger.info(f"Connecting to WebSocket for {pair} price updates.")
                async for ticker in self.exchange.watch_ticker(pair):
                    current_price = ticker['last']
                    timestamp = ticker['timestamp'] / 1000.0  # Convert to seconds
                    on_price_update(current_price, timestamp)
            except Exception as e:
                self.logger.error(f"WebSocket connection error: {e}. Reconnecting...")
                await asyncio.sleep(5)

    async def listen_to_price_updates(self, pair: str, on_price_update: Callable[[float, float], None]):
        await self._subscribe_to_price_updates(pair, on_price_update)

    def close_connection(self):
        self.connection_active = False

    async def get_balance(self):
        try:
            balance = await self.exchange.fetch_balance()
            self.logger.info(f"Retrieved balance: {balance}")
            return balance
        except ccxt.BaseError as e:
            raise DataFetchError(f"Error fetching balance: {str(e)}")
    
    async def get_current_price(self, pair: str):
        try:
            ticker = await self.exchange.fetch_ticker(pair)
            return ticker['last']
        except ccxt.BaseError as e:
            raise DataFetchError(f"Error fetching current price: {str(e)}")

    async def place_order(self, pair: str, order_type: str, amount: float, price: float = None) -> dict:
        try:
            if order_type == "buy":
                order = await self.exchange.create_limit_buy_order(pair, amount, price)
            elif order_type == "sell":
                order = await self.exchange.create_limit_sell_order(pair, amount, price)
            else:
                raise ValueError("Invalid order type specified. Must be 'buy' or 'sell'.")

            self.logger.info(f"Placed {order_type} order: {order}")
            return order

        except ccxt.NetworkError as e:
            self.logger.warning(f"Network error placing {order_type} order for {pair}: {str(e)}.")
            raise DataFetchError(f"Network issue occurred while placing order: {str(e)}")
        except ccxt.BaseError as e:
            self.logger.error(f"Exchange error placing {order_type} order for {pair}: {str(e)}")
            raise DataFetchError(f"Error placing order: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error placing {order_type} order: {str(e)}")
            raise DataFetchError(f"Unexpected error placing order: {str(e)}")

    async def get_order_status(self, order_id: str) -> Dict[str, Union[str, float]]:
        try:
            order = await self.exchange.fetch_order(order_id)
            return order

        except ccxt.NetworkError as e:
            self.logger.error(f"Network error while fetching order {order_id}: {str(e)}")
            raise DataFetchError(f"Network issue occurred while fetching order status: {str(e)}")
        except ccxt.BaseError as e:
            self.logger.error(f"Exchange error while fetching order {order_id}: {str(e)}")
            raise DataFetchError(f"Exchange-specific error occurred: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error while fetching order {order_id}: {str(e)}")
            raise DataFetchError(f"Failed to fetch order status: {str(e)}")

    async def cancel_order(self, order_id: str, pair: str) -> dict:
        try:
            self.logger.info(f"Attempting to cancel order {order_id} for pair {pair}")
            cancellation_result = await self.exchange.cancel_order(order_id, pair)
            
            if cancellation_result['status'] in ['canceled', 'closed']:
                self.logger.info(f"Order {order_id} successfully canceled.")
                return cancellation_result
            else:
                self.logger.warning(f"Order {order_id} cancellation status: {cancellation_result['status']}")
                return cancellation_result

        except ccxt.OrderNotFound as e:
            error_msg = f"Order {order_id} not found for cancellation. It may already be completed or canceled."
            self.logger.warning(error_msg)
            raise OrderCancellationError(error_msg) from e
        except ccxt.NetworkError as e:
            error_msg = f"Network error while canceling order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            raise OrderCancellationError(error_msg) from e
        except ccxt.BaseError as e:
            error_msg = f"Exchange error while canceling order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            raise OrderCancellationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error while canceling order {order_id}: {str(e)}"
            self.logger.error(error_msg)
            raise OrderCancellationError(error_msg) from e

    def fetch_ohlcv(self, pair, timeframe, start_date, end_date):
        raise NotImplementedError("fetch_ohlcv is not used in live or paper trading mode.")