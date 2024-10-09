import logging

def setup_logging(log_level, log_to_file=False, log_file_path=None):
    handlers = []
    handlers.append(logging.StreamHandler())

    if log_to_file:
        if not log_file_path:
            log_file_path = 'grid_trading_bot.log'  # Default log file path if none is provided
        handlers.append(logging.FileHandler(log_file_path))

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )