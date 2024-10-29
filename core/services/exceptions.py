class UnsupportedExchangeError(Exception):
    """Raised when the exchange is not supported."""
    pass

class DataFetchError(Exception):
    """Raised when data fetching fails after retries."""
    pass

class UnsupportedTimeframeError(Exception):
    """Raised when a timeframe is not supported by a given exchange."""
    pass

class OrderCancellationError(Exception):
    """Raised when order cancellation fails."""
    pass

class MissingEnvironmentVariableError(Exception):
    """Raised when env variable are missing (EXCHANGE_API_KEY and/or EXCHANGE_SECRET_KEY)."""
    pass