from typing import List, Dict, Optional, Tuple
from .order import Order, OrderSide, OrderState
from ..grid_management.grid_level import GridLevel

class OrderBook:
    def __init__(self):
        self.buy_orders: List[Order] = []
        self.sell_orders: List[Order] = []
        self.non_grid_orders: List[Order] = []  # Orders that are not linked to any grid level
        self.order_to_grid_map: Dict[Order, GridLevel] = {}  # Mapping of Order -> GridLevel
    
    def add_order(
        self,
        order: Order,
        grid_level: Optional[GridLevel] = None
    ) -> None:
        if order.order_side == OrderSide.BUY:
            self.buy_orders.append(order)
        else:
            self.sell_orders.append(order)

        if grid_level:
            self.order_to_grid_map[order] = grid_level # Store the grid level associated with this order
        else:
            self.non_grid_orders.append(order) # This is a non-grid order like take profit or stop loss
    
    def get_buy_orders_with_grid(self) -> List[Tuple[Order, Optional[GridLevel]]]:
        return [(order, self.order_to_grid_map.get(order, None)) for order in self.buy_orders]
    
    def get_sell_orders_with_grid(self) -> List[Tuple[Order, Optional[GridLevel]]]:
        return [(order, self.order_to_grid_map.get(order, None)) for order in self.sell_orders]

    def get_non_grid_orders(self) -> List[Order]:
        return self.non_grid_orders
    
    def get_all_buy_orders(self) -> List[Order]:
        return self.buy_orders

    def get_all_sell_orders(self) -> List[Order]:
        return self.sell_orders
    
    def get_pending_orders(self) -> List[Order]:
        return [order for order in self.buy_orders + self.sell_orders if order.is_pending()]

    def get_completed_orders(self) -> List[Order]:
        return [order for order in self.buy_orders + self.sell_orders if order.is_completed()]

    def update_order_state(
        self, 
        order_id: str, 
        new_state: OrderState
    ) -> None:
        for order in self.buy_orders + self.sell_orders:
            if order.identifier == order_id:
                order.state = new_state
                break