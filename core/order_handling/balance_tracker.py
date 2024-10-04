from validation.exceptions import InsufficientBalanceError, InsufficientCryptoBalanceError

class BalanceTracker:
    def __init__(self, fee_calculator, initial_balance, initial_crypto_balance=0):
        self.fee_calculator = fee_calculator
        self.balance = initial_balance
        self.crypto_balance = initial_crypto_balance
        self.total_fees = 0

    def update_after_buy(self, quantity, price):
        fee = self.fee_calculator.calculate_fee(quantity * price)
        total_cost = quantity * price + fee
        if self.balance < total_cost:
            raise InsufficientBalanceError("Insufficient balance to complete the transaction")
        
        self.balance -= total_cost
        self.crypto_balance += quantity
        self.total_fees += fee

    def update_after_sell(self, quantity, price):
        fee = self.fee_calculator.calculate_fee(quantity * price)
        if self.crypto_balance < quantity:
            raise InsufficientCryptoBalanceError("Insufficient crypto balance to complete the transaction")
        
        self.crypto_balance -= quantity
        self.balance += quantity * price - fee
        self.total_fees += fee
    
    def sell_all(self, price):
        if self.crypto_balance > 0:
            self.update_after_sell(self.crypto_balance, price)