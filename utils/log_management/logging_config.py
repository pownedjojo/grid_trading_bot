import logging, os
from typing import Optional
from datetime import datetime
from utils.log_management.loki_handler import LokiHandler

def setup_logging(
    log_level: int, 
    log_to_file: bool = False, 
    log_file_path: Optional[str] = None, 
    config_name: Optional[str] = None, 
    enable_loki: bool = False, 
    loki_url: Optional[str] = "http://localhost:3100/loki/api/v1/push"
) -> None:
    """
    Sets up logging with options for local file and Loki centralized logging.

    Args:
        log_level (int): The logging level (e.g., logging.INFO, logging.DEBUG).
        log_to_file (bool): Whether to log to a file.
        log_file_path (Optional[str]): Path to the log file (if log_to_file is True).
        config_name (Optional[str]): Name of the bot configuration to differentiate logs.
        enable_loki (bool): Whether to enable Loki centralized logging.
        loki_url (Optional[str]): The URL of the Loki server.
    """
    handlers = []

    # Console logging
    console_handler = logging.StreamHandler()
    handlers.append(console_handler)

    # File logging
    if log_to_file:
        if not log_file_path:
            if config_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_path = f"logs/{config_name}_{timestamp}.log"
            else:
                log_file_path = 'logs/grid_trading_bot.log'  # Default log file path if none is provided
        else:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            file_handler = logging.FileHandler(log_file_path)
            handlers.append(file_handler)

    # Loki centralized logging
    if enable_loki and config_name and loki_url:
        loki_handler = LokiHandler(
            url=loki_url,
            tags={"job": "grid_trading_bot", "config": config_name},
            version="1",
        )
        handlers.append(loki_handler)

    # Logging configuration
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )