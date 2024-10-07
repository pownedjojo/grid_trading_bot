import pytest
from core.order_handling.order import Order, OrderType, OrderState
from core.validation.exceptions import InvalidOrderTypeError

class TestOrder:

    def test_create_order_with_valid_data(self):
        order = Order(price=1000, quantity=5, order_type=OrderType.BUY, timestamp="2024-01-01T00:00:00Z")
        
        assert order.price == 1000
        assert order.quantity == 5
        assert order.order_type == OrderType.BUY
        assert order.timestamp == "2024-01-01T00:00:00Z"
        assert order.state == OrderState.PENDING

    def test_create_order_with_invalid_order_type(self):
        with pytest.raises(InvalidOrderTypeError):
            Order(price=1000, quantity=5, order_type="INVALID_TYPE", timestamp="2024-01-01T00:00:00Z")

    def test_complete_order(self):
        order = Order(price=1000, quantity=5, order_type=OrderType.BUY, timestamp="2024-01-01T00:00:00Z")
        order.complete()
        
        assert order.state == OrderState.COMPLETED
        assert order.is_completed()

    def test_cancel_order(self):
        order = Order(price=1000, quantity=5, order_type=OrderType.SELL, timestamp="2024-01-01T00:00:00Z")
        order.cancel()
        
        assert order.state == OrderState.COMPLETED  # Assuming cancel sets state to COMPLETED (might need adjustment)
        assert order.is_completed()

    def test_is_pending(self):
        order = Order(price=1000, quantity=5, order_type=OrderType.BUY, timestamp="2024-01-01T00:00:00Z")
        
        assert order.is_pending()