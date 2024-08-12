import ccxt
import pandas as pd

def load_data(exchange_name, pair, timeframe, start_date, end_date):
    exchange = getattr(ccxt, exchange_name)()
    since = exchange.parse8601(start_date)
    until = exchange.parse8601(end_date)
    ohlcv = exchange.fetch_ohlcv(pair, timeframe, since, limit=1000)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df[df['timestamp'] <= pd.to_datetime(until, unit='ms')]
    df.set_index('timestamp', inplace=True)
    return df