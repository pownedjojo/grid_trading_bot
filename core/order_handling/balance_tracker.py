from .fee_calculator import FeeCalculator

class BalanceTracker:
    def __init__(
        self, 
        fee_calculator: FeeCalculator, 
        initial_balance: float, 
        initial_crypto_balance: float = 0
    ):
        self.fee_calculator = fee_calculator
        self.balance: float = initial_balance
        self.crypto_balance: float = initial_crypto_balance
        self.total_fees: float = 0

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