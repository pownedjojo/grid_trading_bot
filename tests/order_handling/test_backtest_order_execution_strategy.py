import pytest
from unittest.mock import patch
from core.order_handling.execution_strategy.backtest_order_execution_strategy import BacktestOrderExecutionStrategy
from core.order_handling.order import OrderType, OrderSide

class TestBacktestOrderExecutionStrategy:
    @pytest.fixture
    def strategy(self):
        return BacktestOrderExecutionStrategy()

    @patch("time.time", return_value=1622505600)
    @pytest.mark.asyncio
    async def test_execute_market_order_buy(self, mock_time, strategy):
        order_side = OrderSide.BUY
        order_type = OrderType.MARKET
        pair = "BTC/USD"
        quantity = 1.5
        price = 50000.0

        result = await strategy.execute_market_order(order_side, pair, quantity, price)

        assert result["id"] == "backtest-1622505600", "Order ID should reflect mocked timestamp"
        assert result["pair"] == pair, "Pair should match input pair"
        assert result["side"] == order_side.name, "Order side should match 'BUY'"
        assert result["type"] == order_type, "Order type should match 'MARKET'"
        assert result["filled_qty"] == quantity, "Quantity should match input quantity"
        assert result["price"] == price, "Price should match input price"
        assert result["status"] == "filled", "Order should be immediately filled in backtest mode"

    @patch("time.time", return_value=1622505600)
    @pytest.mark.asyncio
    async def test_execute_market_order_sell(self, mock_time, strategy):
        order_side = OrderSide.SELL
        order_type = OrderType.MARKET
        pair = "ETH/USD"
        quantity = 2.0
        price = 2000.0

        result = await strategy.execute_market_order(order_side, pair, quantity, price)

        assert result["id"] == "backtest-1622505600", "Order ID should reflect mocked timestamp"
        assert result["pair"] == pair, "Pair should match input pair"
        assert result["side"] == order_side.name, "Order side should match 'SELL'"
        assert result["type"] == order_type, "Order type should match 'MARKET'"
        assert result["filled_qty"] == quantity, "Quantity should match input quantity"
        assert result["price"] == price, "Price should match input price"
        assert result["status"] == "filled", "Order should be immediately filled in backtest mode"
    
    @patch("time.time", return_value=1622505600)
    @pytest.mark.asyncio
    async def test_execute_limit_order_buy(self, mock_time, strategy):
        order_side = OrderSide.BUY
        order_type = OrderType.LIMIT
        pair = "BTC/USD"
        quantity = 1.5
        price = 50000.0

        result = await strategy.execute_limit_order(order_side, pair, quantity, price)

        assert result["id"] == "backtest-1622505600", "Order ID should reflect mocked timestamp"
        assert result["pair"] == pair, "Pair should match input pair"
        assert result["side"] == order_side.name, "Order side should match 'BUY'"
        assert result["type"] == order_type, "Order type should match 'LIMIT'"
        assert result["filled_qty"] == quantity, "Quantity should match input quantity"
        assert result["price"] == price, "Price should match input price"
        assert result["status"] == "filled", "Order should be immediately filled in backtest mode"

    @patch("time.time", return_value=1622505600)
    @pytest.mark.asyncio
    async def test_execute_limit_order_sell(self, mock_time, strategy):
        order_side = OrderSide.SELL
        order_type = OrderType.LIMIT
        pair = "ETH/USD"
        quantity = 2.0
        price = 2000.0

        result = await strategy.execute_limit_order(order_side, pair, quantity, price)

        assert result["id"] == "backtest-1622505600", "Order ID should reflect mocked timestamp"
        assert result["pair"] == pair, "Pair should match input pair"
        assert result["side"] == order_side.name, "Order side should match 'SELL'"
        assert result["type"] == order_type, "Order type should match 'LIMIT'"
        assert result["filled_qty"] == quantity, "Quantity should match input quantity"
        assert result["price"] == price, "Price should match input price"
        assert result["status"] == "filled", "Order should be immediately filled in backtest mode"