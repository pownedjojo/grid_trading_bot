import pytest
from unittest.mock import Mock
from core.order_handling.balance_tracker import BalanceTracker
from core.validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError

@pytest.mark.asyncio
class TestBalanceTracker:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.fee_calculator = Mock()
        self.fee_calculator.calculate_fee.side_effect = lambda trade_value: trade_value * 0.01  # 1% fee
        self.balance_tracker = BalanceTracker(self.fee_calculator, initial_balance=1000, initial_crypto_balance=10)

    async def test_update_after_buy_success(self):
        await self.balance_tracker.update_after_buy(quantity=2, price=50)
        
        assert self.balance_tracker.balance == 1000 - (2 * 50 + (2 * 50 * 0.01))  # 100 - 1% fee
        assert self.balance_tracker.crypto_balance == 10 + 2
        assert self.balance_tracker.total_fees == 2 * 50 * 0.01

    async def test_update_after_buy_insufficient_balance(self):
        with pytest.raises(InsufficientBalanceError):
            await self.balance_tracker.update_after_buy(quantity=1000, price=100)  # Too expensive

    async def test_update_after_sell_success(self):
        await self.balance_tracker.update_after_sell(quantity=5, price=200)
        
        assert self.balance_tracker.crypto_balance == 10 - 5
        assert self.balance_tracker.balance == 1000 + (5 * 200 - (5 * 200 * 0.01))  # 1000 + revenue - fee
        assert self.balance_tracker.total_fees == 5 * 200 * 0.01

    async def test_update_after_sell_insufficient_crypto_balance(self):
        with pytest.raises(InsufficientCryptoBalanceError):
            await self.balance_tracker.update_after_sell(quantity=20, price=200)  # More crypto than available

    async def test_sell_all(self):
        await self.balance_tracker.sell_all(price=100)
        
        assert self.balance_tracker.crypto_balance == 0
        assert self.balance_tracker.balance == 1000 + (10 * 100 - (10 * 100 * 0.01))  # Sold all crypto
        assert self.balance_tracker.total_fees == 10 * 100 * 0.01

    async def test_get_total_balance_value(self):
        total_value = await self.balance_tracker.get_total_balance_value(price=200)
        expected_value = 1000 + 10 * 200  # Balance + crypto converted to fiat

        assert total_value == expected_value