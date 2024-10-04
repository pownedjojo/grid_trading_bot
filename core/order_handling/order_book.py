from collections import defaultdict
from .order import OrderType

class OrderBook:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []
        self.non_grid_orders = []  # Orders that are not linked to any grid level
        self.order_to_grid_map = {}  # Mapping of Order -> GridLevel
    
    def add_order(self, order, grid_level=None):
        if order.order_type == OrderType.BUY:
            self.buy_orders.append(order)
        else:
            self.sell_orders.append(order)

        if grid_level:
            self.order_to_grid_map[order] = grid_level # Store the grid level associated with this order
        else:
            self.non_grid_orders.append(order) # This is a non-grid order like take profit or stop loss
    
    def get_buy_orders_with_grid(self):
        return [(order, self.order_to_grid_map.get(order, None)) for order in self.buy_orders]
    
    def get_sell_orders_with_grid(self):
        return [(order, self.order_to_grid_map.get(order, None)) for order in self.sell_orders]

    def get_non_grid_orders(self):
        return self.non_grid_orders

    def get_all_orders(self):
        all_orders = self.buy_orders + self.sell_orders + self.non_grid_orders
        return all_orders
    
    def get_all_buy_orders(self):
        return self.buy_orders

    def get_all_sell_orders(self):
        return self.sell_orders