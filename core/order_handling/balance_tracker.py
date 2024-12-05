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
        self.event_bus.subscribe(Events.ORDER_COMPLETED, self.update_balance_on_order_completion)

    async def update_balance_on_order_completion(self, order: Order) -> None:
        if order.side == OrderSide.BUY:
            await self._update_after_buy_order_completed(order.filled, order.price)
        elif order.side == OrderSide.SELL:
            await self._update_after_sell_order_completed(order.filled, order.price)

    async def _update_after_buy_order_completed(
        self, 
        quantity: float, 
        price: float
    ) -> None:
        fee = self.fee_calculator.calculate_fee(quantity * price)
        total_cost = quantity * price + fee
        self.balance -= total_cost
        self.crypto_balance += quantity
        self.total_fees += fee

    async def _update_after_sell_order_completed(
        self, 
        quantity: float, 
        price: float
    ) -> None:
        fee = self.fee_calculator.calculate_fee(quantity * price)
        self.crypto_balance -= quantity
        self.balance += quantity * price - fee
        self.total_fees += fee
    
    async def get_total_balance_value(
        self, 
        price: float
    ) -> float:
        return self.balance + self.crypto_balance * price
    
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