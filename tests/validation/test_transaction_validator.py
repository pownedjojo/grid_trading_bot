import pytest
from unittest.mock import Mock
from core.validation.transaction_validator import TransactionValidator
from core.validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError

class TestTransactionValidator:
    @pytest.fixture
    def grid_level(self):
        mock_grid_level = Mock()
        mock_grid_level.price = 3000
        return mock_grid_level

    @pytest.fixture
    def validator(self):
        return TransactionValidator()

    def test_validate_buy_order_sufficient_balance(self, validator, grid_level):
        grid_level.can_place_buy_order.return_value = True
        balance = 5000
        quantity = 1
        price = 3000

        try:
            validator.validate_buy_order(balance, quantity, price, grid_level)
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")

    def test_validate_buy_order_insufficient_balance(self, validator, grid_level):
        grid_level.can_place_buy_order.return_value = True
        balance = 2000  # Not enough to buy
        quantity = 1
        price = 3000

        with pytest.raises(InsufficientBalanceError, match="Insufficient balance"):
            validator.validate_buy_order(balance, quantity, price, grid_level)

    def test_validate_sell_order_sufficient_crypto_balance(self, validator, grid_level):
        grid_level.can_place_sell_order.return_value = True
        crypto_balance = 5
        quantity = 3

        try:
            validator.validate_sell_order(crypto_balance, quantity, grid_level)
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")

    def test_validate_sell_order_insufficient_crypto_balance(self, validator, grid_level):
        grid_level.can_place_sell_order.return_value = True
        crypto_balance = 1  # Not enough to sell
        quantity = 3

        with pytest.raises(InsufficientCryptoBalanceError, match="Insufficient crypto balance"):
            validator.validate_sell_order(crypto_balance, quantity, grid_level)

    def test_validate_buy_order_with_tolerance(self, validator, grid_level):
        validator.tolerance = 0.1  # Increase tolerance for test
        grid_level.can_place_buy_order.return_value = True
        balance = 3000.05  # Slightly above the required amount due to tolerance
        quantity = 1
        price = 3000

        try:
            validator.validate_buy_order(balance, quantity, price, grid_level)
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")

    def test_validate_sell_order_with_tolerance(self, validator, grid_level):
        validator.tolerance = 0.1  # Increase tolerance for test
        grid_level.can_place_sell_order.return_value = True
        crypto_balance = 3.05  # Slightly above the required amount due to tolerance
        quantity = 3

        try:
            validator.validate_sell_order(crypto_balance, quantity, grid_level)
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")

    def test_validate_buy_order_with_exact_balance(self, validator, grid_level):
        grid_level.can_place_buy_order.return_value = True
        balance = 3000  # Exact balance needed
        quantity = 1
        price = 3000

        try:
            validator.validate_buy_order(balance, quantity, price, grid_level)
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")

    def test_validate_sell_order_with_exact_crypto_balance(self, validator, grid_level):
        grid_level.can_place_sell_order.return_value = True
        crypto_balance = 3  # Exact crypto balance needed
        quantity = 3

        try:
            validator.validate_sell_order(crypto_balance, quantity, grid_level)
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")