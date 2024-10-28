import ccxt, logging, time, os
import pandas as pd
from utils.constants import CANDLE_LIMITS, TIMEFRAME_MAPPINGS
from .exchange_interface import ExchangeInterface
from .exceptions import UnsupportedExchangeError, DataFetchError, UnsupportedTimeframeError

class BacktestExchangeService(ExchangeInterface):
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.historical_data_file = self.config_manager.get_historical_data_file()
        self.exchange_name = self.config_manager.get_exchange_name()
        self.exchange = self._initialize_exchange()

        ## ADDED: TO CHECK
        self.initial_balance = self.config_manager.get_initial_balance()
        self.fiat_balance = self.initial_balance
        self.crypto_balance = 0
    
    def _initialize_exchange(self):
        try:
            return getattr(ccxt, self.exchange_name)()
        except AttributeError:
            raise UnsupportedExchangeError(f"The exchange '{self.exchange_name}' is not supported.")
    
    def _is_timeframe_supported(self, timeframe):
        supported_timeframes = self.exchange.timeframes
        if timeframe in supported_timeframes:
            return True
        else:
            self.logger.warning(f"Timeframe '{timeframe}' is not supported by {self.exchange_name}.")
            return False
    
    def get_balance(self):
        ## SHOULD NOT BE CALLED ?
        return {"fiat_balance": self.fiat_balance, "crypto_balance": self.crypto_balance}

    def place_order(self, pair, order_type, amount, price=None):
        self.logger.info(f"Simulating {order_type} order: {amount} {pair} at price {price}")
        return {
            'id': f"backtest-{int(time.time())}",
            'pair': pair,
            'type': order_type,
            'amount': amount,
            'price': price,
            'status': 'filled'
        }

    def fetch_ohlcv(self, pair, timeframe, start_date, end_date):
        if self.historical_data_file and os.path.exists(self.historical_data_file):
            self.logger.info(f"Loading OHLCV data from file: {self.historical_data_file}")
            return self._load_ohlcv_from_file(self.historical_data_file, start_date, end_date)

        if not self._is_timeframe_supported(timeframe):
            raise UnsupportedTimeframeError(f"Timeframe '{timeframe}' is not supported by {self.exchange_name}.")

        self.logger.info(f"Fetching OHLCV data for {pair} from {start_date} to {end_date}")
        try:
            since = self.exchange.parse8601(start_date)
            until = self.exchange.parse8601(end_date)
            candles_per_request = self._get_candle_limit()
            total_candles_needed = (until - since) // self._get_timeframe_in_ms(timeframe)

            if total_candles_needed > candles_per_request:
                return self._fetch_ohlcv_in_chunks(pair, timeframe, since, until, candles_per_request)
            else:
                return self._fetch_ohlcv_single_batch(pair, timeframe, since, until)
        except ccxt.NetworkError as e:
            raise DataFetchError(f"Network issue occurred while fetching OHLCV data: {str(e)}")
        except ccxt.BaseError as e:
            raise DataFetchError(f"Exchange-specific error occurred: {str(e)}")
        except Exception as e:
            raise DataFetchError(f"Failed to fetch OHLCV data {str(e)}.")
    
    def _load_ohlcv_from_file(self, file_path, start_date, end_date):
        try:
            df = pd.read_csv(file_path, parse_dates=['timestamp'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            start_timestamp = pd.to_datetime(start_date).tz_localize(None)
            end_timestamp = pd.to_datetime(end_date).tz_localize(None)
            filtered_df = df.loc[start_timestamp:end_timestamp]
            self.logger.info(f"Loaded {len(filtered_df)} rows of OHLCV data from file.")
            return filtered_df
        except Exception as e:
            raise DataFetchError(f"Failed to load OHLCV data from file: {str(e)}")

    def _fetch_ohlcv_single_batch(self, pair, timeframe, since, until):
        ohlcv = self._fetch_with_retry(self.exchange.fetch_ohlcv, pair, timeframe, since)
        return self._format_ohlcv(ohlcv, until)

    def _fetch_ohlcv_in_chunks(self, pair, timeframe, since, until, candles_per_request):
        all_ohlcv = []
        while since < until:
            ohlcv = self._fetch_with_retry(self.exchange.fetch_ohlcv, pair, timeframe, since, limit=candles_per_request)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            self.logger.info(f"Fetched up to {pd.to_datetime(since, unit='ms')}")
        return self._format_ohlcv(all_ohlcv, until)

    def _format_ohlcv(self, ohlcv, until):
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        until_timestamp = pd.to_datetime(until, unit='ms')
        return df[df.index <= until_timestamp]
    
    def _get_candle_limit(self):
        return CANDLE_LIMITS.get(self.exchange_name, 500)  # Default to 500 if not found

    def _get_timeframe_in_ms(self, timeframe):
        return TIMEFRAME_MAPPINGS.get(timeframe, 60 * 1000)  # Default to 1m if not found

    def _fetch_with_retry(self, method, *args, retries=3, delay=5, **kwargs):
        for attempt in range(retries):
            try:
                return method(*args, **kwargs)
            except Exception as e:
                if attempt < retries - 1:
                    self.logger.warning(f"Attempt {attempt+1} failed. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Failed after {retries} attempts: {e}")
                    raise DataFetchError(f"Failed to fetch data after {retries} attempts: {str(e)}")

    def get_current_price(self, pair):
        pass

    def get_order_status(self, order_id):
        pass

    def cancel_order(self, order_id):
        pass