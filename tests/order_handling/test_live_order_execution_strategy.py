import pytest
from unittest.mock import AsyncMock
from core.order_handling.execution_strategy.live_order_execution_strategy import LiveOrderExecutionStrategy
from core.order_handling.order import OrderType, OrderSide
from core.services.exchange_interface import ExchangeInterface
from core.order_handling.exceptions import OrderExecutionFailedError

class TestLiveOrderExecutionStrategy:
    @pytest.fixture
    def mock_exchange_service(self):
        return AsyncMock(spec=ExchangeInterface)

    @pytest.fixture
    def strategy(self, mock_exchange_service):
        return LiveOrderExecutionStrategy(exchange_service=mock_exchange_service)

    @pytest.mark.asyncio
    async def test_execute_market_order_full_fill_first_attempt(self, strategy, mock_exchange_service):
        mock_order = {'status': 'filled', 'id': 'order123', 'filled': 1.5}
        mock_exchange_service.place_order.return_value = mock_order

        result = await strategy.execute_market_order(OrderSide.BUY, "BTC/USD", 1.5, 50000)

        assert result['status'] == 'filled'
        assert result['id'] == 'order123'
        mock_exchange_service.place_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_market_order_partial_fill_retry(self, strategy, mock_exchange_service):
        # Mock the exchange service to return a partially filled order on the first attempt
        partial_order = {'status': 'partially_filled', 'id': 'order123', 'filled_qty': 0.5, 'remaining_qty': 1.0}
        mock_exchange_service.place_order.return_value = partial_order
        mock_exchange_service.cancel_order.return_value = {'status': 'canceled'}

        # Mock a full fill after retrying
        mock_exchange_service.place_order.side_effect = [partial_order, {'status': 'filled', 'id': 'order123', 'filled': 1.5}]

        result = await strategy.execute_market_order(OrderSide.BUY, "BTC/USD", 1.5, 50000)

        assert result['status'] == 'filled'
        assert result['id'] == 'order123'
        assert result['filled_qty'] == 1.5
        assert mock_exchange_service.cancel_order.await_count == 1, "Expected a cancellation attempt for the partial fill"
    
    @pytest.mark.asyncio
    async def test_execute_market_order_all_retries_failed(self, strategy, mock_exchange_service):
        # Simulate order placement failure for all retries
        mock_exchange_service.place_order.side_effect = Exception("Order failed")

        with pytest.raises(OrderExecutionFailedError, match="Failed to execute Market order after maximum retries"):
            await strategy.execute_market_order(OrderSide.BUY, "BTC/USD", 1.5, 50000)

        # Verify that place_order was called `max_retries` times
        assert mock_exchange_service.place_order.await_count == strategy.max_retries

    @pytest.mark.asyncio
    async def test_retry_cancel_order_successful(self, strategy, mock_exchange_service):
        mock_exchange_service.cancel_order.return_value = {'status': 'canceled'}

        result = await strategy._retry_cancel_order("order123", "BTC/USD")

        assert result is True, "Expected cancellation to succeed after retries"
        assert mock_exchange_service.cancel_order.await_count == 1

    @pytest.mark.asyncio
    async def test_adjust_price_sell(self, strategy):
        original_price = 100.0
        adjusted_price_first_attempt = await strategy._adjust_price(OrderSide.SELL, original_price, attempt=1)
        adjusted_price_second_attempt = await strategy._adjust_price(OrderSide.SELL, original_price, attempt=2)

        assert adjusted_price_first_attempt < original_price, "Adjusted price should be lower for SELL orders on the first attempt"
        assert adjusted_price_second_attempt < adjusted_price_first_attempt, "Adjusted price should decrease further on the second attempt"
    
    @pytest.mark.asyncio
    async def test_adjust_price_buy(self, strategy):
        original_price = 100.0
        adjusted_price_first_attempt = await strategy._adjust_price(OrderSide.BUY, original_price, attempt=1)
        adjusted_price_second_attempt = await strategy._adjust_price(OrderSide.BUY, original_price, attempt=2)

        assert adjusted_price_first_attempt > original_price, "Adjusted price should be higher for BUY orders on the first attempt"
        assert adjusted_price_second_attempt > adjusted_price_first_attempt, "Adjusted price should increase further on the second attempt"
    
    @pytest.mark.asyncio
    async def test_handle_partial_fill_cancel_success(self, strategy):
        order_result = {'id': 'order_123', 'status': 'partially_filled', 'filled_qty': 1.0}
        strategy.exchange_service.cancel_order = AsyncMock(return_value={'status': 'canceled'})

        result = await strategy._handle_partial_fill(order_result, "BTC/USD")

        assert result is None, "Expected None when partial order cancelation succeeds"

    @pytest.mark.asyncio
    async def test_retry_cancel_order_success(self, strategy):
        strategy.exchange_service.cancel_order = AsyncMock(return_value={'status': 'canceled'})
        result = await strategy._retry_cancel_order("order_123", "BTC/USD")

        assert result is True, "Expected cancelation to succeed when status is 'canceled'"

    @pytest.mark.asyncio
    async def test_retry_cancel_order_failure(self, strategy):
        strategy.exchange_service.cancel_order = AsyncMock(return_value={'status': 'open'})  # Simulate failure on all attempts
        result = await strategy._retry_cancel_order("order_123", "BTC/USD")

        assert result is False, "Expected cancelation to fail after max retry attempts"