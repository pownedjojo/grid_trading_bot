import pytest
from unittest.mock import Mock, AsyncMock
from core.order_handling.balance_tracker import BalanceTracker
from core.bot_management.event_bus import EventBus, Events
from core.order_handling.order import Order, OrderSide
from core.validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError

class TestBalanceTracker:
    @pytest.fixture
    def setup_balance_tracker(self):
        event_bus = Mock(spec=EventBus)
        fee_calculator = Mock()
        balance_tracker = BalanceTracker(event_bus, fee_calculator, initial_balance=1000, initial_crypto_balance=5)
        return balance_tracker, fee_calculator, event_bus

    def test_initialization(self, setup_balance_tracker):
        balance_tracker, _, _ = setup_balance_tracker
        assert balance_tracker.balance == 1000
        assert balance_tracker.crypto_balance == 5
        assert balance_tracker.total_fees == 0
        assert balance_tracker.reserved_fiat == 0
        assert balance_tracker.reserved_crypto == 0

    def test_reserve_funds_for_buy(self, setup_balance_tracker):
        balance_tracker, _, _ = setup_balance_tracker
        balance_tracker.reserve_funds_for_buy(200)
        assert balance_tracker.reserved_fiat == 200
        assert balance_tracker.balance == 800

    def test_reserve_funds_for_buy_insufficient_balance(self, setup_balance_tracker):
        balance_tracker, _, _ = setup_balance_tracker
        with pytest.raises(InsufficientBalanceError):
            balance_tracker.reserve_funds_for_buy(1200)

    def test_reserve_funds_for_sell(self, setup_balance_tracker):
        balance_tracker, _, _ = setup_balance_tracker
        balance_tracker.reserve_funds_for_sell(2)
        assert balance_tracker.reserved_crypto == 2
        assert balance_tracker.crypto_balance == 3

    def test_reserve_funds_for_sell_insufficient_balance(self, setup_balance_tracker):
        balance_tracker, _, _ = setup_balance_tracker
        with pytest.raises(InsufficientCryptoBalanceError):
            balance_tracker.reserve_funds_for_sell(10)

    def test_get_adjusted_fiat_balance(self, setup_balance_tracker):
        balance_tracker, _, _ = setup_balance_tracker
        balance_tracker.reserve_funds_for_buy(200)
        assert balance_tracker.get_adjusted_fiat_balance() == 1000

    def test_get_adjusted_crypto_balance(self, setup_balance_tracker):
        balance_tracker, _, _ = setup_balance_tracker
        balance_tracker.reserve_funds_for_sell(2)
        assert balance_tracker.get_adjusted_crypto_balance() == 5

    def test_update_after_buy_order_completed(self, setup_balance_tracker):
        balance_tracker, fee_calculator, _ = setup_balance_tracker
        fee_calculator.calculate_fee.return_value = 10
        balance_tracker.reserved_fiat = 500
        balance_tracker._update_after_buy_order_completed(quantity=1, price=100)
        assert balance_tracker.crypto_balance == 6
        assert balance_tracker.total_fees == 10
        assert balance_tracker.reserved_fiat == 390

    def test_update_after_sell_order_completed(self, setup_balance_tracker):
        balance_tracker, fee_calculator, _ = setup_balance_tracker
        fee_calculator.calculate_fee.return_value = 10
        balance_tracker.reserved_crypto = 2
        balance_tracker._update_after_sell_order_completed(quantity=1, price=200)
        assert balance_tracker.balance == 1190
        assert balance_tracker.total_fees == 10
        assert balance_tracker.reserved_crypto == 1

    # @pytest.mark.asyncio
    # async def test_update_balance_on_order_completion(self, setup_balance_tracker):
    #     balance_tracker, fee_calculator, _ = setup_balance_tracker
    #     fee_calculator.calculate_fee.return_value = 5  # Mock fee calculation

    #     # Mock buy order completion
    #     buy_order = Mock(side=OrderSide.BUY, filled=1, price=100)
    #     balance_tracker.reserved_fiat = 105  # Reserved fiat for the buy order (price + fee)
    #     await balance_tracker._update_balance_on_order_completion(buy_order)
    #     assert balance_tracker.crypto_balance == 6  # Crypto balance increases by 1
    #     assert balance_tracker.total_fees == 5  # Total fees reflect the buy order fee
    #     assert balance_tracker.reserved_fiat == 0  # Reserved fiat should be fully consumed
    #     assert balance_tracker.balance == 895  # Remaining balance after the buy order

    #     # Mock sell order completion
    #     sell_order = Mock(side=OrderSide.SELL, filled=1, price=200)
    #     balance_tracker.reserved_crypto = 1  # Reserved crypto for the sell order
    #     await balance_tracker._update_balance_on_order_completion(sell_order)
    #     assert balance_tracker.crypto_balance == 5  # Crypto balance decreases by 1
    #     assert balance_tracker.total_fees == 10  # Total fees include the sell order fee
    #     assert balance_tracker.reserved_crypto == 0  # Reserved crypto should be fully consumed
    #     assert balance_tracker.balance == 1195  # Remaining balance after the sell order

    def test_get_total_balance_value(self, setup_balance_tracker):
        balance_tracker, _, _ = setup_balance_tracker
        assert balance_tracker.get_total_balance_value(price=200) == 2000

    def test_event_subscription(self, setup_balance_tracker):
        balance_tracker, _, event_bus = setup_balance_tracker
        event_bus.subscribe.assert_called_once_with(Events.ORDER_COMPLETED, balance_tracker._update_balance_on_order_completion)