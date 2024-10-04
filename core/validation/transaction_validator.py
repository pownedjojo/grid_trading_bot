from .exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError, GridLevelNotReadyError

class TransactionValidator:
    def __init__(self, tolerance=1e-6):
        self.tolerance = tolerance

    def validate_buy_order(self, balance, quantity, price, grid_level):
        self._check_balance(balance, quantity, price, grid_level)
        self._check_grid_level(grid_level, is_buy=True)

    def validate_sell_order(self, crypto_balance, quantity, grid_level):
        self._check_crypto_balance(crypto_balance, quantity, grid_level)
        self._check_grid_level(grid_level, is_buy=False)

    def _check_balance(self, balance, quantity, price, grid_level):
        total_cost = quantity * price
        if balance < total_cost - self.tolerance:
            raise InsufficientBalanceError(f"Insufficient balance: {balance} < {total_cost} to place buy order at grid level {grid_level.price}.")

    def _check_crypto_balance(self, crypto_balance, quantity, grid_level):
        if crypto_balance < quantity - self.tolerance:
            raise InsufficientCryptoBalanceError(f"Insufficient crypto balance: {crypto_balance} < {quantity} to place sell order at grid level {grid_level.price}.")

    def _check_grid_level(self, grid_level, is_buy=True):
        if is_buy and not grid_level.can_place_buy_order():
            raise GridLevelNotReadyError(f"Grid level {grid_level.price} is not ready for a buy order.")
        if not is_buy and not grid_level.can_place_sell_order():
            raise GridLevelNotReadyError(f"Grid level {grid_level.price} is not ready for a sell order.")
