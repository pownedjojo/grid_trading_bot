import argparse, logging
from utils import load_config
from data.exchanges import load_data
from strategies.grid import GridTradingStrategy
from config.logging_config import setup_logging

def main(config_path):
    config = load_config(config_path)

    log_level = config['logging'].get('log_level', 'INFO').upper()
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting Grid Trading Bot")

    exchange = config['exchange']['name']
    pair = f"{config['pair']['base_currency']}/{config['pair']['quote_currency']}"
    timeframe = config['timeframe']
    start_date = config['period']['start_date']
    end_date = config['period']['end_date']

    logger.info(f"Loading data from {exchange} for {pair} from {start_date} to {end_date}")
    data = load_data(exchange, pair, timeframe, start_date, end_date)
    
    strategy = GridTradingStrategy(config)
    strategy.data = data
    strategy.simulate()
    strategy.plot_results()
    performance_summary = strategy.calculate_performance_metrics()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest Spot Grid Trading Strategy.")
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file.')
    args = parser.parse_args()
    main(args.config)