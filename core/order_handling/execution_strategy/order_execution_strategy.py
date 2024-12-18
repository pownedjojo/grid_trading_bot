from abc import ABC, abstractmethod
from typing import Optional
from ..order import Order, OrderSide

class OrderExecutionStrategy(ABC):
    @abstractmethod
    async def execute_market_order(
        self, 
        order_side: OrderSide, 
        pair: str, 
        quantity: float,
        price: float
    ) -> Optional[Order]:
        pass

    @abstractmethod
    async def execute_limit_order(
        self, 
        order_side: OrderSide, 
        pair: str, 
        quantity: float, 
        price: float
    ) -> Optional[Order]:
        pass

    @abstractmethod
    async def get_order(
        self, 
        order_id: str,
        pair: str
    ) -> Optional[Order]:
        pass