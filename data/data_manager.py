import ccxt
import logging
import pandas as pd
from .exceptions import UnsupportedExchangeError, DataFetchError

class DataManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.exchange_name = self.config_manager.get_exchange_name()
        try:
            self.exchange = getattr(ccxt, self.exchange_name)()
        except AttributeError:
            raise UnsupportedExchangeError(f"The exchange '{self.exchange_name}' is not supported.")

    def fetch_ohlcv(self, pair, timeframe, start_date, end_date):
        self.logger.info(f"Fetching OHLCV data for {pair} from {start_date} to {end_date}")
        try:
            since = self.exchange.parse8601(start_date)
            until = self.exchange.parse8601(end_date)
            candles_per_request = self._get_candle_limit()
            total_candles_needed = (until - since) // self._get_timeframe_in_ms(timeframe)

            if total_candles_needed > candles_per_request:
                return self._fetch_ohlcv_in_chunks(pair, timeframe, since, until, candles_per_request)
            else:
                return self._fetch_ohlcv_once(pair, timeframe, since, until)
        except Exception as e:
            raise DataFetchError(f"Failed to fetch OHLCV data {str(e)}.")

    def _fetch_ohlcv_once(self, pair, timeframe, since, until):
        ohlcv = self._fetch_with_retry(self.exchange.fetch_ohlcv, pair, timeframe, since)
        df = self._format_ohlcv(ohlcv)
        return df[df.index <= until]

    def _fetch_ohlcv_in_chunks(self, pair, timeframe, since, until, candles_per_request):
        all_ohlcv = []
        while since < until:
            ohlcv = self._fetch_with_retry(self.exchange.fetch_ohlcv, pair, timeframe, since, limit=candles_per_request)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
        
        return self._format_ohlcv(all_ohlcv)

    def _format_ohlcv(self, ohlcv):
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    
    def _get_candle_limit(self):
        candle_limits = {
            'binance': 1000,
            'coinbase': 300,
            'kraken': 720,
            'bitfinex': 5000
        }
        return candle_limits.get(self.exchange_name, 500) # Default to 500 if not found

    def _get_timeframe_in_ms(self, timeframe):
        timeframe_mappings = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        return timeframe_mappings.get(timeframe, 60 * 1000)  # Default to 1m if not found

    def _fetch_with_retry(self, method, *args, retries=3, delay=5, **kwargs):
        for attempt in range(retries):
            try:
                return method(*args, **kwargs)
            except Exception as e:
                if attempt < retries - 1:
                    self.logger.warning(f"Attempt {attempt+1} failed. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise DataFetchError(f"Failed to fetch data after {retries} attempts: {str(e)}")