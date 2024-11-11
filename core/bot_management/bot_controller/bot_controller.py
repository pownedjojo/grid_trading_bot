import logging, asyncio
from tabulate import tabulate
from strategies.grid_trading_strategy import GridTradingStrategy
from core.order_handling.balance_tracker import BalanceTracker
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from .exceptions import CommandParsingError, BalanceRetrievalError, OrderRetrievalError, StrategyControlError

class BotController:
    def __init__(
        self, 
        strategy: GridTradingStrategy, 
        balance_tracker: BalanceTracker, 
        trading_performance_analyzer: TradingPerformanceAnalyzer, 
        stop_event: asyncio.Event
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.strategy = strategy
        self.balance_tracker = balance_tracker
        self.trading_performance_analyzer = trading_performance_analyzer
        self.stop_event = stop_event
        self._stop_listener = False

    async def command_listener(self):
        self.logger.info("Command listener started. Type 'quit' to exit.")
        loop = asyncio.get_event_loop()
        
        while not self._stop_listener:
            try:
                command = await loop.run_in_executor(None, input, "Enter command (quit, orders, balance, stop, restart, pause): ")
                await self._handle_command(command.strip().lower())
            except CommandParsingError as e:
                self.logger.warning(f"Command error: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error in command listener: {e}", exc_info=True)

    async def _handle_command(self, command: str):
        if command == "quit":
            self.logger.info("HealthCheck will be stopped.")
            self.stop_event.set()
            await self.stop_listener()
            await self._shutdown_bot()
        
        elif command == "orders":
            await self._display_orders()
        
        elif command == "balance":
            await self._display_balance()

        elif command == "stop":
            await self._stop_strategy()

        elif command == "restart":
            await self._restart_strategy()
        
        elif command.startswith("pause"):
            await self._pause_bot(command)
        
        else:
            raise CommandParsingError(f"Unknown command: {command}")

    async def stop_listener(self):
        self._stop_listener = True
        self.logger.info("Command listener stopped.")

    async def _shutdown_bot(self):
        try:
            self.logger.info("Shutting down bot...")
            await self.strategy.stop()

        except Exception as e:
            raise StrategyControlError(f"Error stopping the bot: {e}")

    async def _display_orders(self):
        try:
            formatted_orders = self.trading_performance_analyzer.get_formatted_orders()
            orders_table = tabulate(formatted_orders, headers=["Order Side", "Type", "Price", "Quantity", "Timestamp", "Grid Level", "Slippage"], tablefmt="pipe")
            self.logger.info("\nFormatted Orders:\n" + orders_table)

        except Exception as e:
            raise OrderRetrievalError(f"Error retrieving orders: {e}")

    async def _display_balance(self):
        try:
            current_balance = self.balance_tracker.balance
            crypto_balance = self.balance_tracker.crypto_balance
            self.logger.info(f"Current Fiat balance: {current_balance}")
            self.logger.info(f"Current Crypto balance: {crypto_balance}")

        except Exception as e:
            raise BalanceRetrievalError(f"Error retrieving balance: {e}")

    async def _stop_strategy(self):
        try:
            await self.strategy.stop()
            self.logger.info("Trading halted successfully.")

        except Exception as e:
            raise StrategyControlError(f"Error stopping the strategy: {e}")

    async def _restart_strategy(self):
        try:
            await self.strategy.restart()
            self.logger.info("Trading resumed successfully.")

        except Exception as e:
            raise StrategyControlError(f"Error restarting the strategy: {e}")

    async def _pause_bot(self, command: str):
        try:
            duration = int(command.split()[1])
            await self.strategy.stop()
            self.logger.info(f"Bot paused for {duration} seconds.")
            await asyncio.sleep(duration)
            self.logger.info("Resuming bot after pause.")
            await self.strategy.restart()

        except ValueError:
            raise CommandParsingError("Invalid pause duration. Please specify in seconds.")
            
        except Exception as e:
            raise StrategyControlError(f"Error during pause operation: {e}")