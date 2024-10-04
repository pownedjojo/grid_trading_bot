import pytest

@pytest.fixture
def valid_config():
    """Fixture providing a valid configuration for testing."""
    return {
        "exchange": {
            "name": "binance",
            "trading_fee": 0.001
        },
        "pair": {
            "base_currency": "ETH",
            "quote_currency": "USDT"
        },
        "timeframe": "1h",
        "period": {
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2023-02-01T00:00:00Z"
        },
        "initial_balance": 10000,
        "grid": {
            "num_grids": 10,
            "top_range": 3000,
            "bottom_range": 2000,
            "spacing_type": "arithmetic",
            "grid_spacing": 100,
            "percentage_spacing": 0.05
        },
        "limits": {
            "take_profit": {
                "is_active": True,
                "threshold": 3500
            },
            "stop_loss": {
                "is_active": False,
                "threshold": 1500
            }
        },
        "logging": {
            "log_level": "INFO"
        }
    }