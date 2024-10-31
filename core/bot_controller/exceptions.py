class BotControllerError(Exception):
    """Base exception class for BotController errors."""

class CommandParsingError(BotControllerError):
    """Exception raised when there is an error parsing a command."""

class BalanceRetrievalError(BotControllerError):
    """Exception raised when balance retrieval fails."""

class OrderRetrievalError(BotControllerError):
    """Exception raised when fetching or displaying orders fails."""

class StrategyControlError(BotControllerError):
    """Exception raised when starting, stopping, or restarting the strategy fails."""