class UnsupportedExchangeError(Exception):
    """Raised when the exchange is not supported."""
    pass

class DataFetchError(Exception):
    """Raised when data fetching fails after retries."""
    pass