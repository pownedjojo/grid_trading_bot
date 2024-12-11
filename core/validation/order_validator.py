from .exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError, InvalidOrderQuantityError

class OrderValidator:
    def __init__(self, tolerance: float = 1e-6):
        """
        Initializes the OrderValidator with a specified tolerance.

        Args:
            tolerance (float): Minimum precision tolerance for validation.
        """
        self.tolerance = tolerance

    def adjust_and_validate_buy_quantity(
        self, 
        balance: float, 
        order_quantity: float, 
        price: float
    ) -> float:
        """
        Adjusts and validates the buy order quantity based on the available balance.

        Args:
            balance (float): Available fiat balance.
            order_quantity (float): Requested buy quantity.
            price (float): Price of the asset.

        Returns:
            float: Adjusted and validated buy order quantity.

        Raises:
            InsufficientBalanceError: If the balance is insufficient to place any valid order.
            InvalidOrderQuantityError: If the adjusted quantity is invalid.
        """
        total_cost = order_quantity * price

        if total_cost > balance:
            adjusted_quantity = (balance - self.tolerance) / price

            if adjusted_quantity <= 0:
                raise InsufficientBalanceError(f"Insufficient balance: {balance:.2f} to place any buy order at price {price:.2f}.")
        else:
            adjusted_quantity = order_quantity

        self._validate_quantity(adjusted_quantity, is_buy=True)
        return adjusted_quantity

    def adjust_and_validate_sell_quantity(
        self, 
        crypto_balance: float, 
        order_quantity: float
    ) -> float:
        """
        Adjusts and validates the sell order quantity based on the available crypto balance.

        Args:
            crypto_balance (float): Available crypto balance.
            order_quantity (float): Requested sell quantity.

        Returns:
            float: Adjusted and validated sell order quantity.

        Raises:
            InsufficientCryptoBalanceError: If the crypto balance is insufficient to place any valid order.
            InvalidOrderQuantityError: If the adjusted quantity is invalid.
        """
        if order_quantity > crypto_balance:
            adjusted_quantity = crypto_balance - self.tolerance

            if adjusted_quantity <= 0:
                raise InsufficientCryptoBalanceError(f"Insufficient crypto balance: {crypto_balance:.6f} to place any sell order.")
        else:
            adjusted_quantity = order_quantity

        self._validate_quantity(adjusted_quantity, is_buy=False)
        return adjusted_quantity

    def _validate_quantity(
        self, 
        quantity: float, 
        is_buy: bool
    ) -> None:
        """
        Validates the adjusted order quantity.

        Args:
            quantity (float): Adjusted quantity to validate.
            is_buy (bool): Whether the order is a buy order.

        Raises:
            InvalidOrderQuantityError: If the quantity is invalid.
        """
        if quantity <= 0:
            order_type = "buy" if is_buy else "sell"
            raise InvalidOrderQuantityError(f"Invalid {order_type} quantity: {quantity:.6f}")