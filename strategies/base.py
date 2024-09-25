import logging
from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    def __init__(self, config_manager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.initial_balance, self.trading_fee, self.take_profit, self.is_take_profit_active, self.stop_loss, self.is_stop_loss_active = self.extract_base_config()
        self.balance = self.initial_balance
        self.crypto_balance = 0
        self.start_crypto_balance = 0
        self.data = None
    
    def extract_base_config(self):
        initial_balance = self.config_manager.get_initial_balance()
        trading_fee = self.config_manager.get_trading_fee()
        take_profit = self.config_manager.get_take_profit_threshold()
        is_take_profit_active = self.config_manager.is_take_profit_active()
        stop_loss = self.config_manager.get_stop_loss_threshold()
        is_stop_loss_active = self.config_manager.is_stop_loss_active()
        return initial_balance, trading_fee, take_profit, is_take_profit_active, stop_loss, is_stop_loss_active
    
    def load_data(self, data):
        self.data = data

    def check_take_profit_stop_loss(self, current_price):
        if self.crypto_balance == 0:
            return False

        def trigger_event(event_name, trigger_price):
            self.logger.info(f"{event_name} triggered at {trigger_price}")
            self.balance += self.crypto_balance * trigger_price * (1 - self.trading_fee)
            self.crypto_balance = 0
            return True

        if self.is_take_profit_active and current_price >= self.take_profit:
            return trigger_event("Take profit", self.take_profit)

        if self.is_stop_loss_active and current_price <= self.stop_loss:
            return trigger_event("Stop loss", self.stop_loss)

        return False

    @abstractmethod
    def simulate(self):
        pass

    @abstractmethod
    def plot_results(self):
        pass

    @abstractmethod
    def generate_performance_report(self):
        pass