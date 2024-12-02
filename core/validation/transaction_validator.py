from ..order_handling.order import OrderSide
from ..grid_management.grid_level import GridLevel
from .exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError, GridLevelNotReadyError

class TransactionValidator:
    def __init__(
        self,
        tolerance: float = 1e-6
    ):
        self.tolerance: float = tolerance

    def validate_buy_order(
        self, 
        balance: float, 
        quantity: float, 
        price: float, 
        grid_level: GridLevel
    ) -> None:
        self._check_balance(balance, quantity, price, grid_level)
        self._check_grid_level(grid_level, OrderSide.BUY)

    def validate_sell_order(
        self, 
        crypto_balance: float, 
        quantity: float, 
        grid_level: GridLevel
    ) -> None:
        self._check_crypto_balance(crypto_balance, quantity, grid_level)
        self._check_grid_level(grid_level, OrderSide.SELL)

    def _check_balance(
        self, 
        balance: float, 
        quantity: float, 
        price: float, 
        grid_level: GridLevel
    ) -> None:
        total_cost = quantity * price
        if balance < total_cost - self.tolerance:
            raise InsufficientBalanceError(f"Insufficient balance: {balance} < {total_cost} to place buy order at grid level {grid_level.price}.")

    def _check_crypto_balance(
        self, 
        crypto_balance: float, 
        quantity: float, 
        grid_level: GridLevel
    ) -> None:
        if crypto_balance < quantity - self.tolerance:
            raise InsufficientCryptoBalanceError(f"Insufficient crypto balance: {crypto_balance} < {quantity} to place sell order at grid level {grid_level.price}.")

    def _check_grid_level(
        self, 
        grid_level: GridLevel, 
        order_side: OrderSide
    ) -> None:
        if order_side == OrderSide.BUY:
            if not grid_level.can_place_buy_order():
                raise GridLevelNotReadyError(f"Grid level {grid_level.price} is not ready for a buy order, current state: {grid_level.state}")
        else:  # SELL
            if not grid_level.can_place_sell_order():
                raise GridLevelNotReadyError(f"Grid level {grid_level.price} is not ready for a sell order, current state: {grid_level.state}")
