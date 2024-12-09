from enum import Enum
from typing import List, Optional
from ..order_handling.order import Order

class GridCycleState(Enum):
    READY_TO_BUY = "ready_to_buy"               # Level is ready for a buy order
    WAITING_FOR_BUY_FILL = "waiting_for_buy_fill"  # Buy order placed, waiting for execution
    READY_TO_SELL = "ready_to_sell"             # Level is ready for a sell order
    WAITING_FOR_SELL_FILL = "waiting_for_sell_fill"  # Sell order placed, waiting for execution

class GridLevel:
    def __init__(self, price: float, state: GridCycleState):
        self.price: float = price
        self.buy_orders: List[Order] = []  # Track all buy orders at this level
        self.sell_orders: List[Order] = []  # Track all sell orders at this level
        self.state: GridCycleState = state
        self.paired_grid_level: Optional['GridLevel'] = None  # Dynamically assigned pairing

    def place_buy_order(self, buy_order: Order) -> None:
        """
        Record a buy order at this level and update state.
        """
        self.buy_orders.append(buy_order)
        self.state = GridCycleState.WAITING_FOR_BUY_FILL

    def complete_buy_order(self) -> None:
        """
        Reset the cycle.
        """
        self.state = GridCycleState.READY_TO_BUY

    def place_sell_order(self, sell_order: Order) -> None:
        """
        Record a sell order at this level and update state.
        """
        self.sell_orders.append(sell_order)
        self.state = GridCycleState.WAITING_FOR_SELL_FILL

    def complete_sell_order(self) -> None:
        """
        Reset the cycle.
        """
        self.state = GridCycleState.READY_TO_SELL

    def can_place_buy_order(self) -> bool:
        """
        Check if a buy order can be placed at this level.
        """
        return self.state == GridCycleState.READY_TO_BUY

    def can_place_sell_order(self) -> bool:
        """
        Check if a sell order can be placed at this level.
        """
        return self.state == GridCycleState.READY_TO_SELL

    def __str__(self) -> str:
        latest_buy_order: Optional[Order] = self.buy_orders[-1] if self.buy_orders else None
        latest_sell_order: Optional[Order] = self.sell_orders[-1] if self.sell_orders else None
        return (
            f"GridLevel(price={self.price}, "
            f"state={self.state.name}, "
            f"num_buy_orders={len(self.buy_orders)}, "
            f"num_sell_orders={len(self.sell_orders)}, "
            f"latest_buy_order={latest_buy_order}, "
            f"latest_sell_order={latest_sell_order})"
            f"paired_grid_level={self.paired_grid_level.price if self.paired_grid_level else None})"
        )

    def __repr__(self) -> str:
        return self.__str__()