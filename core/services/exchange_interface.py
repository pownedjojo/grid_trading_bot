from abc import ABC, abstractmethod

class ExchangeInterface(ABC):
    @abstractmethod
    def get_balance(self):
        pass
    
    @abstractmethod
    def place_order(self, pair, order_type, amount, price=None):
        pass
    
    @abstractmethod
    def fetch_ohlcv(self, pair, timeframe, start_date, end_date):
        pass
    
    @abstractmethod
    def get_current_price(self, pair):
        pass

    @abstractmethod
    def get_order_status(self, order_id):
        pass

    @abstractmethod
    def cancel_order(self, order_id):
        pass