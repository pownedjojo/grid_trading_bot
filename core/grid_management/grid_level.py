from enum import Enum
from typing import List, Optional
from ..order_handling.order import Order

class GridCycleState(Enum):
    READY_TO_BUY_OR_SELL = "ready_to_buy_or_sell"
    READY_TO_BUY = "ready_to_buy"               # Level is ready for a buy order
    WAITING_FOR_BUY_FILL = "waiting_for_buy_fill"  # Buy order placed, waiting for execution
    READY_TO_SELL = "ready_to_sell"             # Level is ready for a sell order
    WAITING_FOR_SELL_FILL = "waiting_for_sell_fill"  # Sell order placed, waiting for execution

class GridLevel:
    def __init__(self, price: float, state: GridCycleState):
        self.price: float = price
        self.orders: List[Order] = []  # Track all orders at this level
        self.state: GridCycleState = state
        self.paired_grid_level: Optional['GridLevel'] = None  # Dynamically assigned pairing
    
    def add_order(self, order: Order) -> None:
        """
        Record an order at this level.
        """
        self.orders.append(order)

    def __str__(self) -> str:
        return (
            f"GridLevel(price={self.price}, "
            f"state={self.state.name}, "
            f"num_orders={len(self.orders)}, "
            f"paired_grid_level={self.paired_grid_level.price if self.paired_grid_level else None})"
        )

    def __repr__(self) -> str:
        return self.__str__()