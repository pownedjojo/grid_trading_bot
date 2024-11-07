import ccxt, logging, asyncio, os
import ccxt.pro as ccxtpro
from typing import List, Dict, Union, Callable, Any, Optional
from config.config_manager import ConfigManager
from .exchange_interface import ExchangeInterface
from .exceptions import UnsupportedExchangeError, DataFetchError, OrderCancellationError, MissingEnvironmentVariableError, InvalidOrderTypeError

class LiveExchangeService(ExchangeInterface):
    def __init__(
        self, 
        config_manager: ConfigManager, 
        is_paper_trading_activated: bool
    ):
        self.config_manager = config_manager
        self.is_paper_trading_activated = is_paper_trading_activated
        self.logger = logging.getLogger(__name__)
        self.exchange_name = self.config_manager.get_exchange_name()
        self.api_key = self._get_env_variable("EXCHANGE_API_KEY")
        self.secret_key = self._get_env_variable("EXCHANGE_SECRET_KEY")
        self.exchange = self._initialize_exchange()
        self.connection_active = False
    
    def _get_env_variable(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise MissingEnvironmentVariableError(f"Missing required environment variable: {key}")
        return value

    def _initialize_exchange(self) -> None:
        try:
            exchange = getattr(ccxtpro, self.exchange_name)({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True
            })

            if self.is_paper_trading_activated:
                self._enable_sandbox_mode(exchange)
            return exchange
        except AttributeError:
            raise UnsupportedExchangeError(f"The exchange '{self.exchange_name}' is not supported.")

    def _enable_sandbox_mode(self, exchange) -> None:
        if self.exchange_name == 'binance':
            exchange.urls['api'] = 'https://testnet.binance.vision/api'
        elif self.exchange_name == 'kraken':
            exchange.urls['api'] = 'https://api.demo-futures.kraken.com'
        elif self.exchange_name == 'bitmex':
            exchange.urls['api'] = 'https://testnet.bitmex.com'
        elif self.exchange_name == 'bybit':
            exchange.set_sandbox_mode(True)
        else:
            self.logger.warning(f"No sandbox mode available for {self.exchange_name}. Running in live mode.")
    
    async def _subscribe_to_ticker_updates(
        self,
        pair: str, 
        on_ticker_update: Callable[[float, float], None], 
        update_interval: float = 1.0
    ) -> None:
        self.connection_active = True
        
        while self.connection_active:
            try:
                self.logger.info(f"Connecting to WebSocket for {pair} ticker updates.")
                ticker = await self.exchange.watch_ticker(pair)

                if not self.connection_active:
                    break

                current_price = ticker['last']
                timestamp = ticker['timestamp'] / 1000.0  # Convert to seconds

                await on_ticker_update(current_price, timestamp)
                await asyncio.sleep(update_interval)

            except ccxtpro.NetworkError as e:
                self.logger.error(f"Network error while connecting to WebSocket: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

            except ccxtpro.ExchangeError as e:
                self.logger.error(f"Exchange error while fetching ticker for {pair}: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

            except Exception as e:
                self.logger.error(f"WebSocket connection error: {e}. Reconnecting...")
                await asyncio.sleep(5)

            finally:
                if not self.connection_active:
                    self.logger.info(f"Connection to Websocket no longer active.")
                    await self.exchange.close()

    async def listen_to_ticker_updates(
        self, 
        pair: str, 
        on_price_update: Callable[[float, float], None],
        update_interval: float = 1.0
    ) -> None:
        await self._subscribe_to_ticker_updates(pair, on_price_update, update_interval)

    async def close_connection(self) -> None:
        self.connection_active = False

    async def get_balance(self) -> Dict[str, Any]:
        try:
            balance = await self.exchange.fetch_balance()
            self.logger.info(f"Retrieved balance: {balance}")
            return balance

        except ccxt.BaseError as e:
            raise DataFetchError(f"Error fetching balance: {str(e)}")
    
    async def get_current_price(self, pair: str) -> float:
        try:
            ticker = await self.exchange.fetch_ticker(pair)
            return ticker['last']

        except ccxt.BaseError as e:
            raise DataFetchError(f"Error fetching current price: {str(e)}")

    async def place_order(
        self, 
        pair: str, 
        order_type: str, 
        amount: float, 
        price: Optional[float] = None
    ) -> Dict[str, Union[str, float]]:
        try:
            if order_type == "buy":
                order = await self.exchange.create_limit_buy_order(pair, amount, price)
            elif order_type == "sell":
                order = await self.exchange.create_limit_sell_order(pair, amount, price)
            else:
                raise ValueError("Invalid order type specified. Must be 'buy' or 'sell'.")

            self.logger.info(f"Placed {order_type} order: {order}")
            return order

        except ValueError as e:
            raise InvalidOrderTypeError(f"Error placing order: {str(e)}")

        except ccxt.NetworkError as e:
            raise DataFetchError(f"Network issue occurred while placing order: {str(e)}")

        except ccxt.BaseError as e:
            raise DataFetchError(f"Error placing order: {str(e)}")

        except Exception as e:
            raise DataFetchError(f"Unexpected error placing order: {str(e)}")

    async def get_order_status(
        self, 
        order_id: str
    ) -> Dict[str, Union[str, float]]:
        try:
            order = await self.exchange.fetch_order(order_id)
            return order

        except ccxt.NetworkError as e:
            raise DataFetchError(f"Network issue occurred while fetching order status: {str(e)}")

        except ccxt.BaseError as e:
            raise DataFetchError(f"Exchange-specific error occurred: {str(e)}")

        except Exception as e:
            raise DataFetchError(f"Failed to fetch order status: {str(e)}")

    async def cancel_order(
        self, 
        order_id: str, 
        pair: str
    ) -> dict:
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
            raise OrderCancellationError(f"Order {order_id} not found for cancellation. It may already be completed or canceled.")

        except ccxt.NetworkError as e:
            raise OrderCancellationError(f"Network error while canceling order {order_id}: {str(e)}")

        except ccxt.BaseError as e:
            raise OrderCancellationError(f"Exchange error while canceling order {order_id}: {str(e)}")

        except Exception as e:
            raise OrderCancellationError(f"Unexpected error while canceling order {order_id}: {str(e)}")

    def fetch_ohlcv(
        self, 
        pair: str, 
        timeframe: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Union[float, int]]]:
        raise NotImplementedError("fetch_ohlcv is not used in live or paper trading mode.")