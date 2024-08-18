import logging
import numpy as np
from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    def __init__(self, config_manager):
        self.balance = config_manager.get_initial_balance()
        self.crypto_balance = 0
        self.trading_fee = config_manager.get_exchange()['trading_fee']
        limits = config_manager.get_limits()
        self.take_profit = limits['take_profit']
        self.stop_loss = limits['stop_loss']
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data = None
        self.initial_balance = config_manager.get_initial_balance()
        self.start_balance = config_manager.get_initial_balance()
        self.start_crypto_balance = 0
    
    def load_data(self, data):
        self.data = data

    def check_take_profit_stop_loss(self, current_price):
        if self.take_profit['is_active'] and current_price >= self.take_profit['threshold']:
            self.logger.info(f"Take profit triggered at {current_price}")
            self.balance += self.crypto_balance * current_price * (1 - self.trading_fee)
            self.crypto_balance = 0
            return True

        if self.stop_loss['is_active'] and current_price <= self.stop_loss['threshold']:
            self.logger.info(f"Stop loss triggered at {current_price}")
            self.balance += self.crypto_balance * current_price * (1 - self.trading_fee)
            self.crypto_balance = 0
            return True
        return False

    def calculate_roi(self):
        total_value = self.balance + self.crypto_balance * self.data['close'].iloc[-1]
        roi = (total_value - self.initial_balance) / self.initial_balance * 100
        return total_value, roi

    def calculate_drawdown(self):
        peak = self.data['account_value'].expanding(min_periods=1).max()
        drawdown = (peak - self.data['account_value']) / peak * 100
        max_drawdown = drawdown.max()
        return max_drawdown

    def calculate_runup(self):
        trough = self.data['account_value'].expanding(min_periods=1).min()
        runup = (self.data['account_value'] - trough) / trough * 100
        max_runup = runup.max()
        return max_runup

    def calculate_time_in_profit_loss(self):
        time_in_profit = (self.data['account_value'] > self.initial_balance).mean() * 100
        time_in_loss = (self.data['account_value'] <= self.initial_balance).mean() * 100
        return time_in_profit, time_in_loss
    
    def calculate_sharpe_ratio(self):
        risk_free_rate = 0.02  # annual risk free rate 2%
        returns = self.data['account_value'].pct_change().dropna()
        excess_returns = returns - risk_free_rate / 252 # Adjusted daily
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        return round(sharpe_ratio, 2)
    
    def calculate_sortino_ratio(self):
        risk_free_rate = 0.02  # annual risk free rate 2%
        returns = self.data['account_value'].pct_change().dropna()
        excess_returns = returns - risk_free_rate / 252  # Adjusted daily
        downside_returns = excess_returns[excess_returns < 0]
        sortino_ratio = excess_returns.mean() / downside_returns.std() * np.sqrt(252)
        return round(sortino_ratio, 2)

    @abstractmethod
    def simulate(self):
        pass

    @abstractmethod
    def plot_results(self):
        pass

    @abstractmethod
    def calculate_performance_metrics(self):
        pass