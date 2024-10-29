from enum import Enum
from typing import Union
from ..validation.exceptions import InvalidOrderTypeError

class OrderType(Enum):
    BUY = 'buy'
    SELL = 'sell'

class OrderState(Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class Order:
    def __init__(self, price: float, quantity: float, order_type: OrderType, timestamp: Union[int, str]):
        if not isinstance(order_type, OrderType):
            raise InvalidOrderTypeError("Invalid order type")

        self.price = price
        self.quantity = quantity
        self.order_type = order_type
        self.timestamp = timestamp
        self.state = OrderState.PENDING
    
    def complete(self) -> None:
        self.state = OrderState.COMPLETED

    def cancel(self) -> None:
        self.state = OrderState.COMPLETED

    def is_pending(self) -> bool:
        return self.state == OrderState.PENDING

    def is_completed(self) -> bool:
        return self.state == OrderState.COMPLETED
    
    def __str__(self) -> str:
        return f"Order({self.order_type}, price={self.price}, quantity={self.quantity}, timestamp={self.timestamp}, state={self.state})"

    def __repr__(self) -> str:
        return self.__str__()