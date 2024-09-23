from enum import Enum

class OrderType(Enum):
    BUY = 'buy'
    SELL = 'sell'

class OrderState(Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class Order:
    def __init__(self, price, quantity, order_type, timestamp):
        if not isinstance(order_type, OrderType):
            raise ValueError("Invalid order type")

        self.price = price
        self.quantity = quantity
        self.order_type = order_type
        self.timestamp = timestamp
        self.state = OrderState.PENDING
    
    def complete(self):
        self.state = OrderState.COMPLETED

    def cancel(self):
        self.state = OrderState.COMPLETED

    def is_pending(self):
        return self.state == OrderState.PENDING

    def is_completed(self):
        return self.state == OrderState.COMPLETED
    
    def __str__(self):
        return f"Order({self.order_type}, price={self.price}, quantity={self.quantity}, timestamp={self.timestamp}, state={self.state})"

    def __repr__(self):
        return self.__str__()