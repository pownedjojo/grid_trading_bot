from abc import ABC, abstractmethod
from .order import OrderType

class OrderExecutionStrategy(ABC):
    @abstractmethod
    async def execute_order(self, order_type: OrderType, pair: str, quantity: float, price: float) -> dict:
        pass