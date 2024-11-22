from .fee_calculator import FeeCalculator
from .order import Order, OrderSide
from core.bot_management.event_bus import EventBus, Events

class BalanceTracker:
    def __init__(
        self, 
        event_bus: EventBus,
        fee_calculator: FeeCalculator, 
        initial_balance: float, 
        initial_crypto_balance: float = 0
    ):
        self.event_bus = event_bus
        self.fee_calculator = fee_calculator
        self.balance: float = initial_balance
        self.crypto_balance: float = initial_crypto_balance
        self.total_fees: float = 0
        self.event_bus.subscribe(Events.ORDER_COMPLETED, self.update_balance_on_order_completion)

    async def update_balance_on_order_completion(self, order: Order) -> None:
        if order.order_side == OrderSide.BUY:
            await self.update_after_buy(order.quantity, order.price)
        elif order.order_side == OrderSide.SELL:
            await self.update_after_sell(order.quantity, order.price)

    async def update_after_buy(
        self, 
        quantity: float, 
        price: float
    ) -> None:
        fee = self.fee_calculator.calculate_fee(quantity * price)
        total_cost = quantity * price + fee
        self.balance -= total_cost
        self.crypto_balance += quantity
        self.total_fees += fee

    async def update_after_sell(
        self, 
        quantity: float, 
        price: float
    ) -> None:
        fee = self.fee_calculator.calculate_fee(quantity * price)
        self.crypto_balance -= quantity
        self.balance += quantity * price - fee
        self.total_fees += fee
    
    async def sell_all(
        self, 
        price: float
    ) -> None:
        if self.crypto_balance > 0:
            await self.update_after_sell(self.crypto_balance, price)
    
    async def get_total_balance_value(
        self, 
        price: float
    ) -> float:
        return self.balance + self.crypto_balance * price