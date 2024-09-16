import logging
from .order import Order, OrderType

class OrderManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.trading_fee = self.config_manager.get_trading_fee()
        self.trade_percentage = 0.1 ## TODO: trade_percentage based on num_grids instead ? Default to 10%
        self.grid_orders = {}
        self.buy_orders = []
        self.sell_orders = []

    ## TODO: is initialize_grid_orders necessary ?
    def initialize_grid_orders(self, grids):
        self.grid_orders = {price: {'buy_order': None, 'sell_order': None} for price in grids}

    def place_buy_order(self, price, timestamp, balance, crypto_balance):
        quantity = self.trade_percentage * balance / price
        if balance < quantity * price * (1 + self.trading_fee):
            raise ValueError("Insufficient balance to place buy order")

        buy_order = Order(price, quantity, OrderType.BUY, timestamp)
        self.grid_orders[price]['buy_order'] = buy_order
        balance -= quantity * price * (1 + self.trading_fee)
        crypto_balance += quantity
        self.buy_orders.append(buy_order)
        return balance, crypto_balance

    def place_sell_order(self, price, buy_order, timestamp, balance, crypto_balance):
        quantity = buy_order.quantity
        if crypto_balance < quantity:
            raise ValueError("Insufficient crypto balance to place sell order")

        sell_order = Order(price, quantity, OrderType.SELL, timestamp)
        self.grid_orders[buy_order.price]['sell_order'] = sell_order
        balance += quantity * price * (1 - self.trading_fee)
        crypto_balance -= quantity
        self.sell_orders.append(sell_order)
        return balance, crypto_balance
    
    def can_place_buy_order(self, buy_grid_price, current_price):
        return current_price <= buy_grid_price and (self.grid_orders[buy_grid_price]['buy_order'] is None or self.grid_orders[buy_grid_price]['buy_order'].is_completed())
    
    def can_place_sell_order(self, sell_grid_price, current_price):
        buy_order = self.find_buy_order_for_sale(sell_grid_price)
        return buy_order is not None and current_price >= sell_grid_price
    
    def find_buy_order_for_sale(self, sell_grid_price):
        for buy_order in self.buy_orders:
            if buy_order.price < sell_grid_price and buy_order.is_completed() == False:
                return buy_order
        return None
