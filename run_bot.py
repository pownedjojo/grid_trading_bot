import argparse
from main import main

def parse_args():
    parser = argparse.ArgumentParser(description="Run the Spot Grid Trading Bot")
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to the configuration file')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args.config)