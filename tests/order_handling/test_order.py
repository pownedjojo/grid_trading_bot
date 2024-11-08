import pytest
from core.order_handling.order import Order, OrderType, OrderState, OrderSide
from core.validation.exceptions import InvalidOrderTypeError, InvalidOrderSideError

class TestOrder:
    def test_create_order_with_valid_data(self):
        order = Order(identifier="123", price=1000, quantity=5, order_side=OrderSide.BUY, order_type=OrderType.MARKET, timestamp="2024-01-01T00:00:00Z")

        
        assert order.identifier == "123"
        assert order.price == 1000
        assert order.quantity == 5
        assert order.order_side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.timestamp == "2024-01-01T00:00:00Z"
        assert order.state == OrderState.PENDING

    def test_create_order_with_invalid_order_type(self):
        with pytest.raises(InvalidOrderTypeError):
            Order(identifier="123", price=1000, quantity=5, order_side=OrderSide.BUY, order_type="INVALID_TYPE", timestamp="2024-01-01T00:00:00Z")
    
    def test_create_order_with_invalid_order_side(self):
        with pytest.raises(InvalidOrderSideError):
            Order(identifier="123", price=1000, quantity=5, order_side="INVALID_TYPE", order_type=OrderType.MARKET, timestamp="2024-01-01T00:00:00Z")

    def test_complete_order(self):
        order = Order(identifier="123", price=1000, quantity=5, order_side=OrderSide.SELL, order_type=OrderType.MARKET, timestamp="2024-01-01T00:00:00Z")
        order.complete()
        
        assert order.state == OrderState.COMPLETED
        assert order.is_completed()

    def test_cancel_order(self):
        order = Order(identifier="123", price=1000, quantity=5, order_side=OrderSide.SELL, order_type=OrderType.MARKET, timestamp="2024-01-01T00:00:00Z")
        order.cancel()
        
        assert order.state == OrderState.COMPLETED  # Assuming cancel sets state to COMPLETED (might need adjustment)
        assert order.is_completed()

    def test_is_pending(self):
        order = Order(identifier="123", price=1000, quantity=5, order_side=OrderSide.BUY, order_type=OrderType.MARKET, timestamp="2024-01-01T00:00:00Z")
        
        assert order.is_pending()