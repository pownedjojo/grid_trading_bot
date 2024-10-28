import logging
from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Requires implementation of key methods for any concrete strategy.
    """
    def __init__(self, config_manager, balance_tracker):
        """
        Initializes the strategy with the given configuration manager and balance tracker.

        Args:
            config_manager: Provides access to the trading configuration (e.g., exchange, fees).
            balance_tracker: Tracks the balance and crypto balance for the strategy.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.balance_tracker = balance_tracker

    @abstractmethod
    def initialize_strategy(self):
        """
        Method to initialize the strategy with specific settings (grids, limits, etc.).
        Must be implemented by any subclass.
        """
        pass

    @abstractmethod
    def run(self):
        """
        Run the strategy with historical or live data.
        Must be implemented by any subclass.
        """
        pass

    @abstractmethod
    def plot_results(self):
        """
        Plots the strategy performance after simulation.
        Must be implemented by any subclass.
        """
        pass

    @abstractmethod
    def generate_performance_report(self):
        """
        Generates a report summarizing the strategy's performance (ROI, max drawdown, etc.).
        Must be implemented by any subclass.
        """
        pass