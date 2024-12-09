import logging
from .fee_calculator import FeeCalculator
from .order import Order, OrderSide
from core.bot_management.event_bus import EventBus, Events
from ..validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError 

class BalanceTracker:
    def __init__(
        self, 
        event_bus: EventBus,
        fee_calculator: FeeCalculator, 
        initial_balance: float, 
        initial_crypto_balance: float = 0
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.event_bus = event_bus
        self.fee_calculator = fee_calculator
        self.balance: float = initial_balance
        self.crypto_balance: float = initial_crypto_balance
        self.total_fees: float = 0
        self.reserved_fiat = 0.0
        self.reserved_crypto = 0.0
        self.event_bus.subscribe(Events.ORDER_COMPLETED, self._update_balance_on_order_completion)

    async def _update_balance_on_order_completion(self, order: Order) -> None:
        """
        Updates the account balance and crypto balance when an order is completed.

        This method is called when an `ORDER_COMPLETED` event is received. It determines 
        whether the completed order is a buy or sell order and updates the balances 
        accordingly.

        Args:
            order: The completed `Order` object containing details such as the side 
                (BUY/SELL), filled quantity, and price.
        """
        if order.side == OrderSide.BUY:
            self._update_after_buy_order_completed(order.filled, order.price)
        elif order.side == OrderSide.SELL:
            self._update_after_sell_order_completed(order.filled, order.price)

    def _update_after_buy_order_completed(
        self, 
        quantity: float, 
        price: float
    ) -> None:
        """
        Updates the balances after a buy order is completed, including handling reserved funds.

        Deducts the total cost (price * quantity + fee) from the reserved fiat balance,
        releases any unused reserved fiat back to the main balance, adds the purchased
        crypto quantity to the crypto balance, and tracks the fees incurred.

        Args:
            quantity: The quantity of crypto purchased.
            price: The price at which the crypto was purchased (per unit).
        """
        fee = self.fee_calculator.calculate_fee(quantity * price)
        total_cost = quantity * price + fee

        self.reserved_fiat -= total_cost
        if self.reserved_fiat < 0:
            self.balance += self.reserved_fiat  # Adjust with excess reserved fiat
            self.reserved_fiat = 0
    
        self.crypto_balance += quantity
        self.total_fees += fee
        self.logger.info(f"Buy order completed: {quantity} crypto purchased at {price}.")

    def _update_after_sell_order_completed(
        self, 
        quantity: float, 
        price: float
    ) -> None:
        """
        Updates the balances after a sell order is completed, including handling reserved funds.

        Deducts the sold crypto quantity from the reserved crypto balance, releases any
        unused reserved crypto back to the main crypto balance, adds the sale proceeds
        (quantity * price - fee) to the fiat balance, and tracks the fees incurred.

        Args:
            quantity: The quantity of crypto sold.
            price: The price at which the crypto was sold (per unit).
        """
        fee = self.fee_calculator.calculate_fee(quantity * price)
        sale_proceeds = quantity * price - fee
        self.reserved_crypto -= quantity

        if self.reserved_crypto < 0:
            self.crypto_balance += abs(self.reserved_crypto)  # Adjust with excess reserved crypto
            self.reserved_crypto = 0

        self.balance += sale_proceeds
        self.total_fees += fee
        self.logger.info(f"Sell order completed: {quantity} crypto sold at {price}.")

    def reserve_funds_for_buy(
        self, 
        amount: float
    ) -> None:
        """
        Reserves fiat for a pending buy order.

        Args:
            amount: The amount of fiat to reserve.
        """
        if self.balance < amount:
            raise InsufficientBalanceError(f"Insufficient fiat balance to reserve {amount}.")

        self.reserved_fiat += amount
        self.balance -= amount
        self.logger.info(f"Reserved {amount} fiat for a buy order. Remaining fiat balance: {self.balance}.")

    def reserve_funds_for_sell(
        self, 
        quantity: float
    ) -> None:
        """
        Reserves crypto for a pending sell order.

        Args:
            quantity: The quantity of crypto to reserve.
        """
        if self.crypto_balance < quantity:
            raise InsufficientCryptoBalanceError(f"Insufficient crypto balance to reserve {quantity}.")

        self.reserved_crypto += quantity
        self.crypto_balance -= quantity
        self.logger.info(f"Reserved {quantity} crypto for a sell order. Remaining crypto balance: {self.crypto_balance}.")

    def get_adjusted_fiat_balance(self) -> float:
        """
        Returns the fiat balance, including reserved funds.

        Returns:
            float: The total fiat balance including reserved funds.
        """
        return self.balance + self.reserved_fiat

    def get_adjusted_crypto_balance(self) -> float:
        """
        Returns the crypto balance, including reserved funds.

        Returns:
            float: The total crypto balance including reserved funds.
        """
        return self.crypto_balance + self.reserved_crypto

    def get_total_balance_value(self, price: float) -> float:
        """
        Calculates the total account value in fiat, including reserved funds.

        Args:
            price: The current market price of the crypto asset.

        Returns:
            float: The total account value in fiat terms.
        """
        return self.get_adjusted_fiat_balance() + self.get_adjusted_crypto_balance() * price