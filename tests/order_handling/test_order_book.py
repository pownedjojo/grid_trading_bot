import pytest
from unittest.mock import Mock
from core.order_handling.order_book import OrderBook
from core.order_handling.order import OrderType

class TestOrderBook:

    def test_add_buy_order_with_grid(self):
        order_book = OrderBook()
        buy_order = Mock(order_type=OrderType.BUY)
        grid_level = Mock()

        order_book.add_order(buy_order, grid_level)

        assert len(order_book.buy_orders) == 1
        assert order_book.buy_orders[0] == buy_order
        assert order_book.order_to_grid_map[buy_order] == grid_level

    def test_add_sell_order_with_grid(self):
        order_book = OrderBook()
        sell_order = Mock(order_type=OrderType.SELL)
        grid_level = Mock()

        order_book.add_order(sell_order, grid_level)

        assert len(order_book.sell_orders) == 1
        assert order_book.sell_orders[0] == sell_order
        assert order_book.order_to_grid_map[sell_order] == grid_level

    def test_add_non_grid_order(self):
        order_book = OrderBook()
        take_profit_order = Mock(order_type=OrderType.SELL)

        # Add non-grid order without grid level
        order_book.add_order(take_profit_order)

        assert len(order_book.non_grid_orders) == 1
        assert order_book.non_grid_orders[0] == take_profit_order

    def test_get_buy_orders_with_grid(self):
        order_book = OrderBook()
        buy_order = Mock(order_type=OrderType.BUY)
        grid_level = Mock()

        order_book.add_order(buy_order, grid_level)
        buy_orders_with_grid = order_book.get_buy_orders_with_grid()

        assert len(buy_orders_with_grid) == 1
        assert buy_orders_with_grid[0] == (buy_order, grid_level)

    def test_get_sell_orders_with_grid(self):
        order_book = OrderBook()
        sell_order = Mock(order_type=OrderType.SELL)
        grid_level = Mock()

        order_book.add_order(sell_order, grid_level)
        sell_orders_with_grid = order_book.get_sell_orders_with_grid()

        assert len(sell_orders_with_grid) == 1
        assert sell_orders_with_grid[0] == (sell_order, grid_level)

    def test_get_non_grid_orders(self):
        order_book = OrderBook()
        non_grid_order = Mock(order_type=OrderType.SELL)

        order_book.add_order(non_grid_order)

        assert len(order_book.get_non_grid_orders()) == 1
        assert order_book.get_non_grid_orders()[0] == non_grid_order

    def test_get_all_buy_orders(self):
        order_book = OrderBook()
        buy_order_1 = Mock(order_type=OrderType.BUY)
        buy_order_2 = Mock(order_type=OrderType.BUY)

        order_book.add_order(buy_order_1)
        order_book.add_order(buy_order_2)

        all_buy_orders = order_book.get_all_buy_orders()

        assert len(all_buy_orders) == 2
        assert buy_order_1 in all_buy_orders
        assert buy_order_2 in all_buy_orders

    def test_get_all_sell_orders(self):
        order_book = OrderBook()
        sell_order_1 = Mock(order_type=OrderType.SELL)
        sell_order_2 = Mock(order_type=OrderType.SELL)

        order_book.add_order(sell_order_1)
        order_book.add_order(sell_order_2)

        all_sell_orders = order_book.get_all_sell_orders()

        assert len(all_sell_orders) == 2
        assert sell_order_1 in all_sell_orders
        assert sell_order_2 in all_sell_orders