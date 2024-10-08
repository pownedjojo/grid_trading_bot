class FeeCalculator:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.trading_fee = self.config_manager.get_trading_fee()

    def calculate_fee(self, trade_value):
        return trade_value * self.trading_fee