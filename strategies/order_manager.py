import logging

class OrderManager:
    def __init__(self, trade_percentage, trading_fee):
        self.trade_percentage = trade_percentage
        self.trading_fee = trading_fee
        self.grid_orders = {}
        self.buy_orders = []
        self.sell_orders = []

    def initialize_grid_orders(self, grids):
        self.grid_orders = {price: {'buy_quantity': 0, 'sell_quantity': 0, 'buy_cycle_complete': True} for price in grids}

    def place_buy_order(self, price, timestamp, balance, crypto_balance):
        quantity = self.trade_percentage * balance / price
        self.grid_orders[price]['buy_quantity'] += quantity
        self.grid_orders[price]['buy_cycle_complete'] = False
        balance -= quantity * price * (1 + self.trading_fee)
        crypto_balance += quantity
        self.buy_orders.append({'price': price, 'quantity': quantity, 'timestamp': timestamp})
        return balance, crypto_balance

    def place_sell_order(self, price, buy_order, timestamp, balance, crypto_balance):
        quantity = buy_order['quantity']
        self.grid_orders[buy_order['price']]['sell_quantity'] += quantity
        self.grid_orders[buy_order['price']]['buy_cycle_complete'] = True
        balance += quantity * price * (1 - self.trading_fee)
        crypto_balance -= quantity
        self.sell_orders.append({'price': price, 'quantity': quantity, 'timestamp': timestamp})
        return balance, crypto_balance
    
    def can_place_buy_order(self, price):
        return self.grid_orders[price]['buy_cycle_complete']
    
    def can_place_sell_order(self, price, current_price):
        buy_order = self.find_buy_order_for_sale(price)
        return buy_order is not None and current_price >= price
    
    def find_buy_order_for_sale(self, sell_price):
        for order in self.buy_orders:
            if order['price'] < sell_price and self.grid_orders[order['price']]['buy_cycle_complete'] == False:
                return order
        return None
