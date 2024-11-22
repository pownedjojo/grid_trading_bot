from abc import ABC, abstractmethod
from ..order import OrderSide

class OrderExecutionStrategy(ABC):
    @abstractmethod
    async def execute_market_order(
        self, 
        order_side: OrderSide, 
        pair: str, 
        quantity: float,
        price: float
    ) -> dict:
        pass

    @abstractmethod
    async def execute_limit_order(
        self, 
        order_side: OrderSide, 
        pair: str, 
        quantity: float, 
        price: float
    ) -> dict:
        pass

    @abstractmethod
    async def get_order(
        self, 
        order_id: str
    ) -> dict:
        pass