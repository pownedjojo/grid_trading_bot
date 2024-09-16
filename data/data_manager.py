import ccxt
import pandas as pd

class DataManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.exchange_name = self.config_manager.get_exchange_name()
        self.exchange = getattr(ccxt, self.exchange_name)()

    def fetch_ohlcv(self, pair, timeframe, start_date, end_date):
        since = self.exchange.parse8601(start_date)
        until = self.exchange.parse8601(end_date)
        candles_per_request = self._get_candle_limit()
        total_candles_needed = (until - since) // self._get_timeframe_in_ms(timeframe)
        
        if total_candles_needed > candles_per_request:
            return self._fetch_ohlcv_in_chunks(pair, timeframe, since, until, candles_per_request)
        else:
            return self._fetch_ohlcv_once(pair, timeframe, since, until)
        
    def _fetch_ohlcv_once(self, pair, timeframe, since, until):
        ohlcv = self.exchange.fetch_ohlcv(pair, timeframe, since)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[df['timestamp'] <= pd.to_datetime(until, unit='ms')]
        df.set_index('timestamp', inplace=True)
        return df

    def _fetch_ohlcv_in_chunks(self, pair, timeframe, since, until, candles_per_request):
        all_ohlcv = []
        while since < until:
            ohlcv = self.exchange.fetch_ohlcv(pair, timeframe, since, limit=candles_per_request)
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
        
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    
    def _get_candle_limit(self):
        # if self.exchange_name == 'binance':
        #     return 1000
        return 1000

    def _get_timeframe_in_ms(self, timeframe):
        timeframe_mappings = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000
        }
        return timeframe_mappings.get(timeframe, 60 * 1000)  # Default to 1m if not found