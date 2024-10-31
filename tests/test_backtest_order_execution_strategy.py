import pytest, time
from unittest.mock import patch
from core.order_handling.backtest_order_execution_strategy import BacktestOrderExecutionStrategy
from core.order_handling.order import OrderType

class TestBacktestOrderExecutionStrategy:
    @pytest.fixture
    def strategy(self):
        return BacktestOrderExecutionStrategy()

    @patch("time.time", return_value=1622505600)
    @pytest.mark.asyncio
    async def test_execute_order_buy(self, mock_time, strategy):
        order_type = OrderType.BUY
        pair = "BTC/USD"
        quantity = 1.5
        price = 50000.0

        result = await strategy.execute_order(order_type, pair, quantity, price)

        assert result["id"] == "backtest-1622505600", "Order ID should reflect mocked timestamp"
        assert result["pair"] == pair, "Pair should match input pair"
        assert result["type"] == order_type.name, "Order type should match 'BUY'"
        assert result["quantity"] == quantity, "Quantity should match input quantity"
        assert result["price"] == price, "Price should match input price"
        assert result["status"] == "filled", "Order should be immediately filled in backtest mode"

    @patch("time.time", return_value=1622505600)
    @pytest.mark.asyncio
    async def test_execute_order_sell(self, mock_time, strategy):
        order_type = OrderType.SELL
        pair = "ETH/USD"
        quantity = 2.0
        price = 2000.0

        result = await strategy.execute_order(order_type, pair, quantity, price)

        assert result["id"] == "backtest-1622505600", "Order ID should reflect mocked timestamp"
        assert result["pair"] == pair, "Pair should match input pair"
        assert result["type"] == order_type.name, "Order type should match 'SELL'"
        assert result["quantity"] == quantity, "Quantity should match input quantity"
        assert result["price"] == price, "Price should match input price"
        assert result["status"] == "filled", "Order should be immediately filled in backtest mode"