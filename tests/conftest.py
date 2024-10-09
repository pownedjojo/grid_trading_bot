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
        "trading_settings": {
            "timeframe": "1m",
            "period": {
            "start_date": "2024-07-04T00:00:00Z",
            "end_date": "2024-07-11T00:00:00Z"
            },
            "initial_balance": 10000
        },
        "grid_strategy": {
            "num_grids": 20,
            "range": {
            "top": 3100,
            "bottom": 2850
            },
            "spacing": {
            "type": "arithmetic",
            "fixed_spacing": 200,
            "percentage_spacing": 0.05
            },
            "trade_percentage": 0.1
        },
        "risk_management": {
            "take_profit": {
            "enabled": False,
            "threshold": 3700
            },
            "stop_loss": {
            "enabled": False,
            "threshold": 2830
            }
        },
        "logging": {
            "log_level": "INFO",
            "log_to_file": True,
            "log_file_path": "logs/trading.log"
        }
    }