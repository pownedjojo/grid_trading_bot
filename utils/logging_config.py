import logging, os
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime

def setup_logging(
    log_level: int,
    log_to_file: bool = False,
    log_file_path: Optional[str] = None,
    config_name: Optional[str] = None,
    max_file_size: int = 5_000_000,  # 5MB default max file size for rotation
    backup_count: int = 5  # Default number of backup files
) -> None:
    """
    Sets up logging with options for console, rotating file logging, and log differentiation.

    Args:
        log_level (int): The logging level (e.g., logging.INFO, logging.DEBUG).
        log_to_file (bool): Whether to log to a file.
        log_file_path (Optional[str]): Path to the log file (if log_to_file is True).
        config_name (Optional[str]): Name of the bot configuration to differentiate logs.
        max_file_size (int): Maximum size of log file in bytes before rotation.
        backup_count (int): Number of backup log files to keep.
    """
    handlers = []

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    handlers.append(console_handler)

    if log_to_file:
        if not log_file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir = 'logs'
            os.makedirs(log_dir, exist_ok=True)
            if config_name:
                log_file_path = os.path.join(log_dir, f"{config_name}_{timestamp}.log")
            else:
                log_file_path = os.path.join(log_dir, 'grid_trading_bot.log')

        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        file_handler = RotatingFileHandler(log_file_path, maxBytes=max_file_size, backupCount=backup_count)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        handlers.append(file_handler)

    logging.basicConfig(level=log_level, handlers=handlers)

    logging.info(f"Logging initialized. Log level: {logging.getLevelName(log_level)}")
    if log_to_file:
        logging.info(f"File logging enabled. Logs are stored in: {log_file_path}")