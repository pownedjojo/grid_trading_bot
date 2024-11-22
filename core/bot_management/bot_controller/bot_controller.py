import logging, asyncio
from tabulate import tabulate
from core.bot_management.event_bus import EventBus, Events
from core.bot_management.grid_trading_bot import GridTradingBot
from .exceptions import CommandParsingError, BalanceRetrievalError, OrderRetrievalError, StrategyControlError

class BotController:
    """
    Handles user commands and manages the lifecycle of the GridTradingBot.
    """

    def __init__(
        self, 
        bot: GridTradingBot, 
        event_bus: EventBus
    ):
        """
        Initializes the BotController.

        Args:
            bot: The GridTradingBot instance to control.
            event_bus: The EventBus instance to publish/subscribe Events.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bot = bot
        self.event_bus = event_bus
        self._stop_listening = False
        self.event_bus.subscribe(Events.STOP_BOT, self._handle_stop_event)

    async def command_listener(self):
        """
        Listens for user commands and processes them.
        """
        self.logger.info("Command listener started. Type 'quit' to exit.")
        loop = asyncio.get_event_loop()
        
        while not self._stop_listening:
            try:
                command = await loop.run_in_executor(None, input, "Enter command (quit, orders, balance, stop, restart, pause): ")
                await self._handle_command(command.strip().lower())

            except CommandParsingError as e:
                self.logger.warning(f"Command error: {e}")

            except Exception as e:
                self.logger.error(f"Unexpected error in command listener: {e}", exc_info=True)

    async def _handle_command(self, command: str):
        """
        Handles individual commands from the user.

        Args:
            command: The command entered by the user.
        """
        if command == "quit":
            self.logger.info("Stopping the bot...")
            self._stop_listener()
            self.event_bus.publish_sync(Events.STOP_BOT, "User requested shutdown")
        
        elif command == "orders":
            await self._display_orders()
        
        elif command == "balance":
            await self._display_balance()

        elif command == "stop":
            self.event_bus.publish_sync(Events.STOP_BOT, "User issued stop command")

        elif command == "restart":
            self.event_bus.publish_sync(Events.STOP_BOT, "User issued restart command")
            self.event_bus.publish_sync(Events.START_BOT, "User issued restart command")
        
        elif command.startswith("pause"):
            await self._pause_bot(command)
        
        else:
            raise CommandParsingError(f"Unknown command: {command}")

    def _stop_listener(self):
        """
        Stops the command listener loop.
        """
        self._stop_listening = True
        self.logger.info("Command listener stopped.")
    
    def _handle_stop_event(self, reason: str) -> None:
        """
        Handles the STOP_BOT event and stops the command listener.

        Args:
            reason: The reason for stopping the bot.
        """
        self.logger.info(f"Received STOP_BOT event: {reason}")
        self._stop_listener()

    async def _display_orders(self):
        """
        Displays formatted orders retrieved from the bot.
        """
        try:
            formatted_orders = self.bot.strategy.get_formatted_orders()
            orders_table = tabulate(formatted_orders, headers=["Order Side", "Type", "Price", "Quantity", "Timestamp", "Grid Level", "Slippage"], tablefmt="pipe")
            self.logger.info("\nFormatted Orders:\n" + orders_table)

        except Exception as e:
            raise OrderRetrievalError(f"Error retrieving orders: {e}")

    async def _display_balance(self):
        """
        Displays the current balances retrieved from the bot.
        """
        try:
            current_balance = self.bot.balance_tracker.balance
            crypto_balance = self.bot.balance_tracker.crypto_balance
            self.logger.info(f"Current Fiat balance: {current_balance}")
            self.logger.info(f"Current Crypto balance: {crypto_balance}")

        except Exception as e:
            raise BalanceRetrievalError(f"Error retrieving balance: {e}")

    async def _pause_bot(self, command: str):
        """
        Pauses the bot for a specified duration.

        Args:
            command: The pause command containing the duration.
        """
        try:
            duration = int(command.split()[1])
            self.event_bus.publish(Events.STOP_BOT, "User issued pause command")
            self.logger.info(f"Bot paused for {duration} seconds.")
            await asyncio.sleep(duration)
            self.logger.info("Resuming bot after pause.")
            self.event_bus.publish(Events.START_BOT, "Resuming bot after pause")

        except ValueError:
            raise CommandParsingError("Invalid pause duration. Please specify in seconds.")
            
        except Exception as e:
            raise StrategyControlError(f"Error during pause operation: {e}")