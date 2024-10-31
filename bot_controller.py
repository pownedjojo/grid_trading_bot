import logging, asyncio
from tabulate import tabulate
from strategies.grid_trading_strategy import GridTradingStrategy
from core.order_handling.balance_tracker import BalanceTracker
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer

class BotController:
    def __init__(self, strategy: GridTradingStrategy, balance_tracker: BalanceTracker, trading_performance_analyzer: TradingPerformanceAnalyzer):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.strategy = strategy
        self.balance_tracker = balance_tracker
        self.trading_performance_analyzer = trading_performance_analyzer
        self._stop_listener = False

    async def command_listener(self):
        self.logger.info("Command listener started. Type 'quit' to exit.")
        loop = asyncio.get_event_loop()
        
        while not self._stop_listener:
            command = await loop.run_in_executor(None, input, "Enter command (quit, orders, balance, stop, restart): ")
            command = command.strip().lower()

            if command == "quit":
                self.logger.info("Shutting down bot...")
                await self.stop_listener()
                self.strategy.stop()

            elif command == "orders":
                formatted_orders = self.trading_performance_analyzer.get_formatted_orders()
                orders_table = tabulate(formatted_orders, headers=["Order Type", "Price", "Quantity", "Timestamp", "Grid Level", "Slippage"], tablefmt="pipe")
                self.logger.info("\nFormatted Orders:\n" + orders_table)

            elif command == "balance":
                current_balance = self.balance_tracker.balance
                crypto_balance = self.balance_tracker.crypto_balance
                self.logger.info(f"Current Fiat balance: {current_balance}")
                self.logger.info(f"Current Crypto balance: {crypto_balance}")

            elif command == "stop":
                await self.strategy.stop()
                self.logger.info("Stop command received, trading halted.")

            elif command == "restart":
                await self.strategy.restart()
                self.logger.info("Restart command received, trading resumed.")
            
            elif command.startswith("pause"): # pause 300 for 5 minutes
                try:
                    duration = int(command.split()[1])
                    await self.strategy.stop()
                    self.logger.info(f"Bot paused for {duration} seconds.")
                    await asyncio.sleep(duration)
                    self.logger.info("Resuming bot after pause.")
                    await self.strategy.restart()
                except ValueError:
                    self.logger.warning("Invalid pause duration. Please specify in seconds.")

            else:
                self.logger.warning("Unknown command. Available commands: quit, orders, balance, stop, restart")

    async def stop_listener(self):
        self._stop_listener = True
        self.logger.info("Command listener stopped.")
